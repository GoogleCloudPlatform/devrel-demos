# Update packages
sudo apt update
sudo apt upgrade

# Download credentials and copy file over to Pi
echo "export GOOGLE_APPLICATION_CREDENTIALS=/user/google/.keys/key.json"  >> ~/.bashrc
. .bashrc

# Install venv
sudo apt install python3-venv python==3.10

# Create virtual env
python3 -m venv sensors

# Activate virtual env
. sensors/bin/activate

# Install requirements
python3 -m pip install -r requirements.txt 

# Turn on SPI for RFID reader
sudo raspi-config nonint do_spi 0

# Clone repo
git clone https://github.com/GoogleCloudPlatform/devrel-demos.git
cd devrel-demos/data-analytics/data-dash/pi

echo ". sensors/bin/activate" >> ~/.bashrc
echo "python run.py > /dev/null 2>&1 &" >> ~/.bashrc

# Set some VIM confg (optional)
# echo "set number" >> .vimrc
# echo "set backspace=indent,eol,start" >> .vimrc
# echo "set nocompatible" >> .vimrc