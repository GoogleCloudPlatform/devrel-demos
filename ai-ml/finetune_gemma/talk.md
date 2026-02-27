Build AI architectures with open models on Cloud Run


Abstract: 
Modern AI architectures are increasingly leveraging specialized open models to deliver high-performance application features with greater efficiency. In this talk, we demonstrate how Cloud Run’s serverless GPU architecture provides a scalable, cost-effective runtime for these workloads without the complexity of managing clusters.
We will walk through a repeatable workflow to:
• Host the latest DeepMind open-weights model, Gemma 4, on serverless GPU instances for low-latency inference with highly differentiated performance, including 5-second cold starts.
• Harness the power of the NVIDIA RTX Pro 6000 GPU to scale your AI with the simplicity and pay-per-use efficiency of Cloud Run.
• Briefly cover Gemma fine tuning using Cloud Run jobs as part of a complete production lifecycle.
Attendees will walk away with a blueprint for hosting high-performance open models that bridge the gap between deep domain expertise and the agility of serverless execution


The talk flow:
1. The Serverless AI Era & Initial Open Model Deployment
   * The Hook: Introduce the problem (managing GPU infrastructure) and the solution: combining the simplicity of Cloud Run with the power of NVIDIA RTX 6000 Pro GPUs.1
   * Live Demo 1: Deploy the base open model (Gemma 3 4B[a][b][c][d][e][f]) live on Cloud Run. Highlight the deployment command and the GPU hardware flags.234
   * Serverless GPU Benefits: Discuss the hardware deep-dive, emphasizing the 96GB VRAM and the cost efficiency of scaling from zero to a fully operational GPU in seconds.1
2. Build and Baseline the Image Analysis Web Application
   * Deploy a Next.js application on Cloud Run that serves as the frontend for our Vision AI system.
   * The app features a clean interface for image uploads and a model selector to switch between different Gemma 3 backends.
   * Connect it to the deployed base Gemma model and show baseline performance on pet breed identification. Highlight that while capable, general models may struggle with specific domain expertise.
3. Explain the Fine-Tuning Pipeline and Cloud Run Jobs
   * Introduce the need for a custom model to improve domain-specific performance.
   * Walk through the fine-tuning architecture using Cloud Run Jobs with GPUs (a new feature and key message).
   * Explain the benefits of fine-tuning, highlighting the developer experience: triggering the job (like the running gemma3-finetuning-job), writing the tuned weights to a bucket, and spinning down automatically.
4. Deploy the Custom Model and Demonstrate Improvement
   * Deploy the fine-tuned model (a custom-tuned version of Gemma 3 27B) to a new Cloud Run service.
   * Use the Next.js app to switch to the new fine-tuned backend.
   * Demonstrate the improvement in results on the same images, comparing the custom model's output against the original baseline and showing higher accuracy in breed identification.
5. Elastic Customer Spotlight: Scaling Custom Models
   * Guest: Customer (Elastic).
   * The Use Case: Elastic discusses their Model-as-a-Service (MaaS) platform and how they use Cloud Run to manage 100+ different custom models.1
   * Customer Demonstration of Scaling: Elastic shows how their custom-tuned models handle massive, concurrent image/data processing workloads using a load generator script.1
   * Show the Google Cloud Console metrics dashboard spiking, demonstrating Cloud Run's ability to instantly scale the production custom model service from zero to many instances to handle the load.
   * Key Metrics: Elastic highlights cost savings from pay-by-the-second billing versus traditional infrastructure like GKE/Compute Engine.1
6. Wrap-Up & Source Code
   * Recap the key takeaways: serverless infrastructure + efficient custom models + agent frameworks = fast path to scaling enterprise AI.
   * Call to Action: A QR code on the screen leading to a GitHub repo containing the code and deployment files.


[a]Let's try a bigger model if possible. One that needs RTX 6000 Pro.
google/gemma-3-27b-it-qat-q4_0-gguf
Needs ~50GB
[b]I'll try
[c]Also trying to use your bucket to download the bigger model to a europe-west4 bucket
[d]google/gemma-3-27b-it-qat-q4_0-gguf didn't work for me for some reason.
[e]I have gemma-3-27b running:  https://pantheon.corp.google.com/run/detail/europe-west4/gemma-3--rtx-6000-w1-gpu-service/revisions?project=shir-training
[f]Cool I was able to fine tune Gemma3 27b
[g]Or web application with UI