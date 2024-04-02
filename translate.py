import sqlite3
from uuid import UUID, uuid4
import hashlib
from googletrans import Translator as GoogleTranslator


def hash_password(password: str) -> str:
    binary_password = password.encode()
    hashed_password = hashlib.sha512(binary_password)
    return hashed_password.hexdigest()


class User:
    def __init__(self, user_id: UUID, phone: str, username: str, password: str):
        self.__user_id = user_id
        self.__phone = phone
        self.__username = username
        self.__password = hash_password(password)

    def __repr__(self) -> str:
        return f"User(id: {self.__user_id}, username: {self.__username}, phone: {self.__phone})"

    @property
    def username(self) -> str:
        return self.__username

    @property
    def password(self) -> str:
        return self.__password

    @property
    def user_id(self) -> UUID:
        return self.__user_id


class Controller:
    def __init__(self, db_file: str):
        self.__current_user = None
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file)
        self.create_tables()
        self.translator = GoogleTranslator()
        self.source_lang = "en"
        self.target_lang = "ru"

    def create_tables(self):
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                                id TEXT PRIMARY KEY,
                                username TEXT UNIQUE,
                                password TEXT,
                                phone TEXT
                              )"""
        )
        self.conn.commit()

    def signup(self) -> None:
        user_id = str(uuid4())
        username = input("Введите ваш ник для регистрации: ")
        password = input("Введите ваш пароль для регистрации: ")
        hashed_password = hash_password(password)
        phone = input("Введите ваш номер телефона для регистрации: ")

        # Проверяем, существует ли пользователь с таким же именем
        cursor = self.conn.execute("SELECT * FROM users WHERE username=?", (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            print(
                "Пользователь с таким именем уже существует. Пожалуйста, выберите другое имя."
            )
            return

        self.conn.execute(
            "INSERT INTO users (id, username, password, phone) VALUES (?, ?, ?, ?)",
            (user_id, username, hashed_password, phone),
        )
        self.conn.commit()
        print("Вы успешно зарегистрировались!")

    def auth_user(self) -> None:
        while True:
            username = input("Введите ваш ник для входа: ")
            password = input("Введите ваш пароль для входа: ")
            hashed_password = hash_password(password)

            cursor = self.conn.execute(
                "SELECT * FROM users WHERE username=? AND password=?",
                (username, hashed_password),
            )
            user = cursor.fetchone()
            if user:
                print("Вы успешно вошли в аккаунт!")
                self.__current_user = User(UUID(user[0]), user[3], user[1], user[2])
                return
            print("Неверно введены данные, пожалуйста, повторите")

    def logout(self) -> None:
        self.__current_user = None
        print("Вы успешно вышли из аккаунта!")

    def set_languages(self) -> None:
        self.source_lang = input(
            "Введите язык ввода (например, 'en' для английского): "
        )
        self.target_lang = input("Введите язык вывода (например, 'ru' для русского): ")

    def change_languages(self) -> None:
        self.source_lang, self.target_lang = self.target_lang, self.source_lang

    def get_current_user(self):
        return self.__current_user


class Translator:
    def __init__(self, db_file: str):
        self.conn = sqlite3.connect(db_file)
        self.create_translation_table()

    def create_translation_table(self):
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS translations (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                source_text TEXT,
                                translated_text TEXT,
                                source_lang TEXT,
                                target_lang TEXT,
                                user_id TEXT,
                                FOREIGN KEY(user_id) REFERENCES users(id)
                              )"""
        )
        self.conn.commit()

    def translate(
        self, source_text: str, source_lang: str, target_lang: str, user_id: UUID
    ) -> str:
        translated_text = self._perform_translation(
            source_text, source_lang, target_lang
        )
        self._save_translation(
            source_text, translated_text, source_lang, target_lang, user_id
        )
        return translated_text

    def _perform_translation(
        self, source_text: str, source_lang: str, target_lang: str
    ) -> str:
        translator = GoogleTranslator()
        translated_text = translator.translate(
            source_text, src=source_lang, dest=target_lang
        ).text
        return translated_text

    def _save_translation(
        self,
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        user_id: UUID,
    ) -> None:
        self.conn.execute(
            "INSERT INTO translations (source_text, translated_text, source_lang, target_lang, user_id) VALUES (?, ?, ?, ?, ?)",
            (source_text, translated_text, source_lang, target_lang, str(user_id)),
        )
        self.conn.commit()

    def get_translation_history(self, user_id: UUID) -> list:
        cursor = self.conn.execute(
            "SELECT source_text, translated_text, source_lang, target_lang FROM translations WHERE user_id=?",
            (str(user_id),),
        )
        translation_history = cursor.fetchall()
        return translation_history


if __name__ == "__main__":
    db_file = "translator.db"

    # экземпляр контроллера
    controller = Controller(db_file)

    # Регистрация
    controller.signup()

    # Вход
    controller.auth_user()

    # Установка языков ввода и вывода
    controller.set_languages()

    # Ввод текста
    source_text = input("Введите текст для перевода: ")

    # текущий пользователь
    current_user = controller.get_current_user()

    if current_user is not None:
        # экземпляр переводчика
        translator = Translator(db_file)

        # Перевод текста
        translated_text = translator.translate(
            source_text,
            controller.source_lang,
            controller.target_lang,
            current_user.user_id,
        )

        print("Переведенный текст:", translated_text)

        # Вывод информации  о выбранных языках ввода-вывода
        print(
            "Текущая пара языков ввода-вывода:",
            controller.source_lang,
            "->",
            controller.target_lang,
        )

        # Смена языков
        controller.change_languages()

        # Выход
        controller.logout()
    else:
        print("Для перевода текста необходимо сначала войти в аккаунт.")
