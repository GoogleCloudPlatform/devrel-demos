## Applications

The backend compute infra for BLB is distributed into 3 applications that work independently.

* Loader application is for generating and sending HTTP traffic
* User Application is the front for receiving HTTP traffic from Loader and 
  distributing it according to user inputs. 
* Worker application is processing received HTTP traffic and generates score
