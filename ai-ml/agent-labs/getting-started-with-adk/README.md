# Getting Started with Agent Development Kit (ADK)

This code sample shows the end-state of the code created in this [Getting Started with Agent Development Kit (ADK)](https://www.cloudskillsboost.google/catalog_lab/32017) lab. 

Author: [Mollie Pettit](https://github.com/molliemarie)

## Overview

This lab covers orchestrating multi-agent systems within the Google Agent Development Kit (Google ADK).

This lab assumes that you are familiar with the basics of ADK and tool use as covered in the labs:

- Get started with Google Agent Development Kit (ADK)
- Empower ADK agents with tools

## Getting Started

### Install Requirements

You'll want to install the requirements to get started. 

```bash
pip3 install -r requirements.txt
```

### Defining `GOOGLE_CLOUD_PROJECT` value

In each agent folder, there is an `.env` file with a line that reads `GOOGLE_CLOUD_PROJECT=YOUR_GOOGLE_CLOUD_PROJECT`. Replace "YOUR_GOOGLE_CLOUD_PROJECT" with the cloud project you'd like to use, in quotes.
