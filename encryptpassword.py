from cryptography.fernet import Fernet

key = Fernet.generate_key()

with open('encryption_key.key','wb') as key_file:
    key_file.write(key)

cipher = Fernet(key)

# change your password here --------
password = b"passwordhere" 
#-----------------------------------

encrypted_password = cipher.encrypt(password)

with open('encrypted_password.txt','wb') as encrypted_file:
    encrypted_file.write(encrypted_password)

print(f"Finish")
