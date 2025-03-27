# stray-auto-authen-kmitl

A **_Python script_** that let you automatically authenticate into KMITL network

## Getting started
### Prerequisites
* Python 3.x
* Git

### Installation
1. Clone repo (notemberg/stray-auto-authen-kmitl)
```
git clone https://github.com/notemberg/stray-auto-authen-kmitl.git
```
2. `cd` into project directory
```
cd stray-auto-authen-kmitl
```
3. Install some essential python packages
```
pip install -r requirements.txt
```
4. generate `encrypted_password.txt` and `encryption_key.key` with encryptpassword.py
```
password = b"passwordhere" 
```
5. edit username and ipaddress in config.json
```
"username":"    ",
"ipAddress": "    ",
```

### Usage
run or set as startup
```
stray_auto_authen.vbs
```

### Config
| Alias | Name | Description |
|:-----:|:----:|-------------|
| `username` | Username | Username to login _(without **@kmitl.ac.th**)_ |
| `ipAddress` | Ip-Address | Ipaddress for local network |
| `time_repeat` | Interval | Heartbeat interval in seconds |
| `max_login_attempt` | Max_Login_Attempt | max login attempts before resetting |

### Credit
* **_assazzin & CSAG_** for original [Auto-authen-KMITL](https://github.com/assazzin/Auto-authen-KMITL) written in Perl language
* **_Network Laboratory_** for original [Auto-authen-KMITL](https://gitlab.com/networklab-kmitl/auto-authen-kmitl) written in Python language Before CSC-KMITL Upgrade Authen Website
* **_CE-HOUSE_** for original [Auto-Authen-KMITL](https://github.com/CE-HOUSE/Auto-Authen-KMITL) written in Python language 
* Core functions from these projects are used in this project under the MIT License. See the included license for more details.

### Project Attribution
This version of stray-auto-authen-kmitl includes additional features and modifications made by [Thinnapat Kharathitipol/notemberg], enhancing the automatic authentication process with added protection and logging features.

## Disclaimer
This project is only an experiment on KMITL authentication system and it does not provided a bypass for login system
