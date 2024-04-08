# Update packages
sudo apt update -y
sudo apt upgrade -y

# Download credentials and copy file over to Pi
echo "export GOOGLE_APPLICATION_CREDENTIALS=/home/google/.keys/key.json"  >> ~/.bashrc
echo "export PROJECT_ID=${1}" >> ~/.bashrc
. .bashrc

# Install venv
sudo apt install python3-venv

# Create virtual env
python3 -m venv sensors

# Activate virtual env
. sensors/bin/activate

# Install requirements
python3 -m pip install -r requirements.txt 

# Turn on SPI for RFID reader
sudo raspi-config nonint do_spi 0

# When the Pi is turned on:
# 1. Activate the Python environment
# 2. Pull the latest version of the demo repo
# 3. Change to the `pi` directly
# 4. Run the script
{
  echo "cd devrel-demos/data-analytics/data-dash/pi"
  echo "git pull https://github.com/GoogleCloudPlatform/devrel-demos.git"
  echo ". sensors/bin/activate"
  echo "python run.py > /dev/null 2>&1 &"
} >> ~/.bashrc

# Set some VIM confg (optional)
# echo "set number" >> ~/.vimrc
# echo "set backspace=indent,eol,start" >> ~/.vimrc
# echo "set nocompatible" >> ~/.vimrc
