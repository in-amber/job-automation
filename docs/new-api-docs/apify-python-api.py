# The Apify API client for Python is the official library that allows you to use
# Linkedin Jobs Scraper API in Python, providing convenience functions and
# automatic retries on errors.

# Install the apify-client with `pip install apify-client`

from apify_client import ApifyClient

# Initialize the ApifyClient with your Apify API token
# Replace '<YOUR_API_TOKEN>' with your token.
client = ApifyClient("<YOUR_API_TOKEN>")

# Prepare the Actor input
run_input = {
    "urls": ["https://www.linkedin.com/jobs/search/?position=1&pageNum=0"],
    "count": 100,
}

# Run the Actor and wait for it to finish
run = client.actor("curious_coder/linkedin-jobs-scraper").call(run_input=run_input)

# Fetch and print Actor results from the run's dataset (if there are any)
print("💾 Check your data here: https://console.apify.com/storage/datasets/" + run["defaultDatasetId"])
for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(item)


# 📚 Want to learn more 📖? Go to → https://docs.apify.com/api/client/python/docs/quick-start
