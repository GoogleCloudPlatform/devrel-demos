This particular demo works as a stand alone, using the %/full directory.
You may also build it yourself using the skeleton and following the instructions below. 

# Overview
In this lab, you will be using Apache Beam (and by extension, Dataflow) to emulate an event center (like a stadium). This is useful as a digital twin but also a great way to demonstrate how a framework such as Apache Beam helps with streaming analytics and AI. 
We will be implementing a myriad of concepts: states, joins, windows, among others, including using multi-modal AI, with Apache Beam.
The inference will use Vertex AI’s Imagen API for a quick and easy way to infer multi-modal requests. Multi-modal means you can provide multiple formats and pieces of information into the model at once. 
In streaming, many pieces need to fit together in order for you to truly benefit and reap the rewards. These include making different pieces of data fit together, from multiple sources, that do not come at the same time. You often don’t have all of the data, at any given moment to make useful decisions. As a data engineer, or data scientist, you can use Apache Beam to build a useful data pipeline, with inference, quickly. 

# What you’ll learn
* How to create an Apache Beam pipeline
* How to pull and join multiple data sources
* How to perform multi-modal inference 
* How to use states in Apache Beam
* How to write to multiple outputs 

# Overview of the pipeline
Note: There are 2 folders, $/skeleton and $/full. 

For those who’d like a challenge, please feel free to use the next paragraph to go ahead and build it all from scratch. 

For those who want to follow along but test your abilities with code, please feel free to use the /skeleton folder. 

For those who want to get a hint or see the full code, please feel free to use the /full folder. Look for the comments, it will have the task number before the code. Please make sure to see if there are multiple comments as some parts of the code are split off. For example, for task 1, look for “Task 2. Read from the various sources”. 

You’ll be tasked to build out this digital twin according to the diagram below. 

The lab will walk you through it step by step but let’s do a quick summary so you can understand how the pieces will fit together. 

First, you’ll read from the various subscriptions. 
You can opt to pull from topics or subscriptions, there is very little practical difference for the purpose of this lab, Beam will create the subscription as needed when pipelines are launched. 

Second, we’ll emulate the member side input lookup. 
To simplify the deployment as much as possible, we will be using the notebook and direct runners to run the Apache Beam code you build. 
There’s a small bug that prevents us from using a pulse (it’s noted in the code) on direct runner; however, the code will be very similar (the input will change) to a real life side input. 

Third, we’ll build a join that will take in two sources (parking and check ins) then print out the actionable information.
We’ll print everything out through standard output (the screen) as it’s the fastest way to get feedback but you have all the tooling and Pub/Sub topics and subscriptions to write it out to Pub/Sub as needed. 

Fourth, we’ll build a custom model handler, this is to interact with the [Vertex AI Imagen Visual-Question and Answering API](https://cloud.google.com/vertex-ai/generative-ai/docs/image/visual-question-answering#use-vqa-short). 
We use a custom model handler as there isn’t one built for this specific API. This also lets you essentially work with any model you would like. We also wrap it in a KeyedModelHandler so you are able to see how to work with keys and inference. This model will take in a URI of an image along with the text “Are there people in this image?”. The API will return a single answer. 

Fifth, we’ll build a stateful function to help determine if there’s a line at a particular area. 
We’ll pass in a message, emulating someone checking if the area is busy or not, and return it.

You can also opt to window and join the elements after the state check, for example, to direct folks to the nearest least busy entrance from the current parking lot. 

Let’s get started!  

Here's the pipeline you'll be building. 
![alt text](https://github.com/GoogleCloudPlatform/devrel-demos/tree/main/data-analytics/beam_multimodal_streaming/pipeline.jpg)

## Task 1. Setup your environment
If you’re using Google Cloud shell or any other CLI, clone the repo into your local directory. 
Clone the repo

```
git clone https://github.com/GoogleCloudPlatform/devrel-demos
```

Change your directory 

```
cd devrel-demos/data-analytics/beam_multimodal_streaming
```

Note down your project ID, you will need this later, also set the environment variable in your code (or shell). You may be able to skip this step if you use Cloud Shell.

```
os.environ['GOOGLE_CLOUD_PROJECT'] = 
```

Create a Google Cloud Storage bucket and upload the necessary files.

```
gcloud storage buckets create gs://${GOOGLE_CLOUD_PROJECT}-gcs/ --location=us-central1
gcloud storage cp *jpg gs://${GOOGLE_CLOUD_PROJECT}-gcs/
gcloud storage cp members.txt gs://${GOOGLE_CLOUD_PROJECT}-gcs/
```

If you are using the skills boost lab, please search for “Colab Enterprise” at the very top. You can import the notebook to get started. 

If you are not using a skills boost lab environment, please open the notebooks with the tool of your choice. 

## Task 2. Read from the various sources
Create 4 pCollections, reading from Pub/Sub sources:
* area_check_logs
* parking_logs
* checkin_logs
* line_logs

Decode them if you’ve read them as bytes and window the parking and check-in logs into 30 second fixed windows. You may need to format them to ensure they can be used in subsequent steps. 

Here’s a sample of each output. 

Parking Logs
```
{'transaction_id': '79d8e1a3-ec2f-4adb-bd26-1c8a11aab14a', 'member_id': None, 'entry_time': 1724343941}
{'transaction_id': 'ebd15695-24d3-46b8-a034-b31ba270bbb9', 'member_id': None, 'entry_time': 1724343941}
```


Are Check Logs
```
{'transaction_id': 'e69579ed-797d-4751-a352-3635a3a1099d', 'area': 'pos'}
{'transaction_id': 'aafa63b5-6752-49ef-a1ea-d64d4096097f', 'area': 'entrance'}
{'transaction_id': '34886d4d-d9ac-40a4-a7c6-e9418ebec8bc', 'area': 'entrance'}
{'transaction_id': '3a3560f2-942c-49ed-94f6-912676f174d8', 'area': 'entrance'}
```

Line Logs
```
{'area': 'entrance', 'image': 'gs://wei-hsia-bigdata-gcs/entrance_empty.jpg'}
{'area': 'pos', 'image': 'gs://wei-hsia-bigdata-gcs/entrance with people.jpg'}
{'area': 'pos', 'image': 'gs://wei-hsia-bigdata-gcs/entrance with people.jpg'}
{'area': 'entrance', 'image': 'gs://wei-hsia-bigdata-gcs/entrance_empty.jpg'}
```

Check-in Logs
```
{'transaction_id': 'aa07a9bf-30b7-4025-8ba1-1f753e5ab727', 'check_in_time': 1724344198, 'member_id': None}
{'transaction_id': '8d6877b4-d4a1-4b8a-8838-fddb7112df4e', 'check_in_time': 1724344309, 'member_id': 'M001'}
{'transaction_id': 'fdfa2d9d-0e30-4676-b291-015701c27f90', 'check_in_time': 1724344331, 'member_id': None}
{'transaction_id': '377a0740-3cfe-4d37-a960-2a67cd5f0481', 'check_in_time': 1724344284, 'member_id': None}
```

Don’t window the area check logs nor the line logs, it’ll unnecessarily complicate your code for the purpose of this lab as [the states are scoped to a key-window combination](https://beam.apache.org/documentation/programming-guide/#state-and-timers). 

## Task 3. Create side input and read
[Due to a bug](https://github.com/apache/beam/issues/21103), we need to emulate this for the direct runner. (For reference, you would want to read in your side input at an interval and then join it.) 

Create a side input, reading from the GCS. 
The code has been provided as it’s not exactly what you would normally expect for a side input. 

```
# Helper function to split apart the GCS URI
def decode_gcs_url(url):
   # Read the URI and parse it
   p = urlparse(url)
   bucket = p.netloc
   file_path = p.path[0:].split('/', 1)
   # Return the relevant objects (bucket, path to object)
   return bucket, file_path[1]


# We can't use the image load from local file since it expects a local path
# We use a GCS URL and get the bytes of the image
def read_file(object_path):
   # Parse the path
   bucket, file_path = decode_gcs_url(object_path)
   storage_client = storage.Client()
   bucket = storage_client.bucket(bucket)
   blob = bucket.blob(file_path)
   # Return the object as bytes
   return blob.download_as_bytes()
```
Helper functions for reading the images, you’ll need this for the inference portion too.

```
def create_side_input():
   all_data = read_file(user_file).decode('utf-8')
   lines = all_data.splitlines()
   user_dict = {}
   for line in lines[1:]:
       user = {}
       member_id,first_name,last_name,parking_benefits,tier = line.split("|")
       user["first_name"] = first_name
       user["last_name"] = last_name
       user["parking_benefits"] = parking_benefits
       user["tier"] = tier
       user_dict[member_id] = user


   return user_dict


class member_lookup(beam.DoFn):
   def __init__(self):
       self.user_dict = None


   def setup(self):
       self.user_dict = create_side_input()


   def teardown(self):
       self.user_dict = None


   def process(self, element):
       lookup = json.loads(element)
       member_id = lookup['member_id']
       if member_id is None:
           return [(None,(None,element))]
       return [(member_id,(self.user_dict[member_id],element))]
```
DoFn for emulating the side input. 

## Task 4. Use the side input to key parking and check-in logs
Use the member_lookup DoFn to key your parking and check-in logs. 
The result will be a key-value pair of member_id, and a tuple that has the member information in a dict alongside the original data. 

## Task 5. Merge the keyed parking and check-in logs
Merge the parking and check-in logs and filter out the ones that do not have at least a record on each side, essentially performing an inner join. (Let’s currently ignore those with multiple, it’s possible due to the parking logs generator.) 

In the example, we filter out records without membership information. You’ll need to handle this in the filter or in the join - as you’ll get a lot of noisy data. 

## Task 6. Output the joined data
For simplicity and instant gratification, let’s print out the data to the console. You can also choose to output it to Pub/Sub as the topics and subscriptions have already been created. 

## Task 7. Create a custom model handler
Create a custom model handler to handle a [Vertex AI API call, here’s the Python SDK for reference](https://cloud.google.com/vertex-ai/generative-ai/docs/image/visual-question-answering#-python). We use a custom model handler as it requires an API call to one that hasn’t been built. 

You’ll want to ask the following question for the purpose of this lab. 
The API we are using will return a short-form response. 
```
question="Are there any people in this picture"
```

## Task 8. RunInference
Use the RunInference turnkey transform to help you perform inference. You’ll also need to use a KeyedModelHandler as the incoming data, we want to preserve a key so we can identify the area. 

In the example, we actually pull in the image bytes first to pass in as an input to the RunInference transform. This is all dependent on how you have built your custom model handler. 

## Task 9. State updates
Create a stateful DoFn, use ReadModifyWriteStateSpec and a StrUtf8Coder. 
Update the state as needed when an update comes in (you can handle this however you want, the example simply reads in the states and updates it). 

Append the state to the data, keep in mind that if you didn’t initialize the original state, you will need to handle that particular scenario. 

You may need to merge your RunInference output and your line logs.

## Task 10. Output the line status
Similar to Task 6, we output to the console for instant gratification; however, you can choose to submit to Pub/Sub if so desired. 

## Task 11. Test the code out
Before running your pipeline, first, use the provided data_generator notebook to create all necessary Pub/Sub topics and subscriptions. 

It also provides you with some minimal sample data (with delays in a streaming fashion). 

Update the variables for your data_generator notebook in the first cell.

```
import os


# Fill In
os.environ['GOOGLE_CLOUD_PROJECT'] = ""
membership_file = ""


# Location where you put your two files in setup
image_with_people = ""
image_empty = ""
```

Run the data_generator notebook, then go back and run your pipeline. 
You should, after a slight delay, see the outputs printing out to console. 

## Congratulations!
You learned how to use joins in a streaming pipeline, use stateful functions, use AI/ML in your streaming pipeline, use a side input in a streaming pipeline, and doing all this while building a multi-input, multi-output, and multi-modal inference data pipeline. You can take it even further by making it multi-model too! Additionally, for the sake of the lab, we didn’t cross the windows for the inference result but you could add a window and now also join as you’d like. 
