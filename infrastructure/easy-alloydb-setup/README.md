# AlloyDB Easy Setup for Development Purposes
This tool helps you link a billing account and spin up an AlloyDB Cluster + Instance (with all other API & network dependencies) using your active Google Cloud credentials.

## Clone the Repo
   
It will open a new tab (make sure you are in the right email account), clone the repository, and enter the directory automatically.

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://ssh.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/AbiramiSukumaran/easy-alloydb-setup&cloudshell_open_in_editor=README.md)


## Run
   
In the Cloud Shell Terminal at the bottom, type the following and hit Enter:

``` bash
sh run.sh
```


## Access UI!

Once the script prints "Starting Server on Port 8080"...

Click the link that you see in the terminal **or**

Click the Web Preview button (looks like an eye 👁️) in the Cloud Shell toolbar.

Select "Preview on port 8080".




## Alternative manual commands for above steps:

1. Run commands in your Cloud Shell Terminal one by one:

``` bash
git clone <<this repo url>>
cd easy-alloydb-setup
sh run.sh
```

2. You should be able to see the url for the app running locally. Access UI by clicking that link!




#### ⚠️⚠️⚠️ Requirements

Permissions: You must have Owner or Editor permissions on the Google Cloud Project you intend to deploy to.

Project: The project must be created before running this tool (the tool handles billing linking, but not project creation).

##### Note: All these steps are listed in detail in this codelab:
[https://codelabs.developers.google.com/quick-alloydb-setup](url)
