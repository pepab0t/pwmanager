import sys, pyperclip
# sys.path.append("res\\utils")
# from db import DBHandler
# from pwgen import PWGenerator
# from hsh import CryptoManager, WrongPasswordError

from ..utils import PWGenerator, DBHandler, CryptoManager, WrongPasswordError

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTableWidgetItem,
    QWidget,
    QDialog,
    QListWidgetItem,
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QStringListModel, QPointF, QPoint
from .gui_login_ui import Ui_LoginWindow
from .gui_pwmanager_ui import Ui_PasswordGUI


def PysideSysAttrSetter(fnc):
    """
    This decorator adds system enviroment, mostly wanted to test this approach
    """

    def add_sys_variables(self):
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
        QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)
        fnc(self)

    return add_sys_variables


class ListItem(object):
    def __init__(self, text="", parent=None):
        super(ListItem, self).__init__()
        self.data = []
        self.text = "Hi!" if not text else text


class LoginWindow(QWidget, Ui_LoginWindow):
    """
    Class for handling PySide LoginWidget
    ## Steps:
        Call LoginWindow
        User fills password
        User presses login button

    ## Important
    You need to add parrent with method "login_successful"

    Args:
        QWidget:
        Ui_LoginWindow:
    """

    def __init__(self, parrent) -> None:
        super().__init__()
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.parrent = parrent
        self._add_events()

    def _add_events(self):
        self.LoginButton.clicked.connect(self.try_to_log_in)
        self.PasswordEdit.installEventFilter(self)
        self.MainPWEdit.installEventFilter(self)
        self.SetPasswordButton.clicked.connect(self._set_new_main_pw)
        # Initialize variables for tracking mouse movements
        self.mousePressPos = None
        self.mouseMovePos = None
        
        self._set_pw_edit_visibity(False)
    
    def _QWidget_pressed(self):
        print("Presses")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mousePressPos = event.globalPosition()
            self.mouseMovePos = event.globalPosition()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            # Calculate the new position of the window
            delta = QPointF(event.globalPosition() - self.mouseMovePos)
            new_pos = self.pos() + QPoint(delta.x(), delta.y())
            self.move(new_pos)
            self.mouseMovePos = event.globalPosition()

    
    def try_to_log_in(self):
        try:
            if self._is_pw_valid_password(self.PasswordEdit.text()):
                self.parrent.login_successful()
            else:
                print("Login was not successful - wrong password")
        except ValueError as e:
            print(e)

    def eventFilter(self, obj, event):
        if obj is self.PasswordEdit and event.type() == event.KeyPress:
            # Check if the pressed key is the Enter key
            if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
                # Call the login method when the Enter key is pressed
                self.try_to_log_in()
                return True  # Event handled
        if obj is self.MainPWEdit and event.type() == event.KeyPress:
            # Check if the pressed key is the Enter key
            if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
                # Call the login method when the Enter key is pressed
                self._set_new_main_pw()
                return True  # Event handled
        return False  # Event not handled

    def _is_pw_valid_password(self, password: str) -> bool:
        """
        Returns True if password is the main password

        1) Find hsh password in DB
        2) Try password: str as a key
        3) If it passes -> you have right pass

        Returns:
            bool: True if password is correct
        """
        try:
            pw_binary = self._find_main_password()
        except ValueError as e:
            raise ValueError(e)

        hsh_handle = CryptoManager(password)
        try:
            hsh_handle.decrypt_string(pw_binary)
            return True
        except WrongPasswordError:
            return False

    def _find_main_password(self) -> bytes:
        db_password = DBHandler()
        try:
            pw_binary = db_password.get_password("MAINPW")
            return pw_binary
        except ValueError as ex:
            self._set_pw_edit_visibity(True)
            raise ValueError("MainPassword was not found - add new one")
            return "".encode()

    def _set_pw_edit_visibity(self, is_visible: bool):
            self.MainPWEdit.setVisible(is_visible)
            self.SetPasswordText.setVisible(is_visible)
            self.SetPasswordButton.setVisible(is_visible)
    
    def _set_new_main_pw(self) -> None:
        new_password = self.MainPWEdit.text()
        db_handle = DBHandler()
        hsh_handle = CryptoManager(new_password)
        pw_bytes = hsh_handle.encrypt_string(new_password)
        db_handle.save_password("MAINPW", pw_bytes)


class PWManagerWindow(QWidget, Ui_PasswordGUI):
    def __init__(self, password = 'Konon') -> None:
        super().__init__()
        # Settup GUI
        self.setupUi(self)

        # Connect events to insturments
        self._add_events()
        
        # Set up database communication
        self.db_handle = DBHandler()
        
        # Set up random password generator
        self.pw_gen = PWGenerator(12)
        
        # Set up crypto manager
        self.hsh_handle = CryptoManager(password)

    def _add_events(self):
        self.AddSiteButton.clicked.connect(self.add_site_button_clicked)
        self.GetPasswordButton.clicked.connect(self.get_password_button_clicked)

        # Create a ListModel for handling displaying passwords
        self.list_model = QStringListModel()

        # Fill QListView instrument with sites
        self._display_sites()

    def add_site_button_clicked(self):
        new_site = self._get_new_site_name()
        new_random_password = self.pw_gen.get_random_password()
        random_password_bytes = self.hsh_handle.encrypt_string(new_random_password)
        self.db_handle.save_password(new_site, random_password_bytes)
        self._display_sites()
        
    def get_password_button_clicked(self):
        site = self.PasswordView.currentIndex().data()
        password_bytes = self.db_handle.get_password(site)
        password_string = self.hsh_handle.decrypt_string(password_bytes)
        pyperclip.copy(password_string)

    def _get_new_site_name(self) -> str:
        return self.SiteEdit.text()
    
    def _display_sites(self):
        # Get sites from database
        db_handle = DBHandler()
        self.list_model.setStringList(db_handle.get_all_sites())

        # Update QListView instrument
        self.PasswordView.setModel(self.list_model)


class MainGuiHandler(QMainWindow, Ui_LoginWindow):
    """
    Call this class to create Password manager app

    Args:
        QMainWindow: _description_
        Ui_LoginWindow (_type_): _description_
    """

    @PysideSysAttrSetter
    def __init__(self) -> None:
        self.app = QApplication(sys.argv)
        # super().__init__()
        self.login_window = LoginWindow(self)
        self.login_window.show()

        # Bypass login - testing
        # self.login_successful()
        sys.exit(self.app.exec())

    def login_successful(self):
        """
        This method is executed after correct login password is passed
        """
        print("Login was successfull")
        # Close Login window
        self.login_window.close()

        # Create window for PWManager and show it
        self.pw_manager_window = PWManagerWindow(self.login_window.PasswordEdit.text())
        self.pw_manager_window.show()


if __name__ == "__main__":
    
    gui = MainGuiHandler()
