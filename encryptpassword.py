from cryptography.fernet import Fernet
import getpass

key = Fernet.generate_key()

with open('encryption_key.key','wb') as key_file:
    key_file.write(key)

cipher = Fernet(key)

# get password --------
password = getpass.getpass("Enter your password: ").encode()
#-----------------------------------

encrypted_password = cipher.encrypt(password)
try:
    with open('encrypted_password.txt','wb') as encrypted_file:
        encrypted_file.write(encrypted_password)
except:
    print("Encryption Failed.")

print("Encryption complete. Encrypted password saved.")
