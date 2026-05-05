# Linkedin Jobs Scraper

## Getting Started [Copy link to clipboard](https://apify.com/curious_coder/linkedin-jobs-scraper\#getting-started)

Scrape jobs from linkedin jobs search results with full job details and optionally details of company posting the job.

This tool scrapes jobs from public version of linkedin jobs search which is **restricted to a few subset of features** supported by advanced version that requires login/cookies to scrape.

If you want accurate jobs search results, boolean search support and additional details such as skills required, then use [Advanced Linkeidn job scraper](https://apify.com/curious_coder/linkedin-jobs-search-scraper)

Go to [linkedin jobs search page](https://www.linkedin.com/jobs/search/), search with required filters and once you are done, copy the full URL from address bar and pass it to this actor.

For scraping jobs from other platforms, the [Indeed Scraper](https://apify.com/curious_coder/indeed-scraper) extracts detailed job data from Indeed search with unlimited scraping at a fixed rental cost. You can also use the [XING Scraper](https://apify.com/curious_coder/xing-scraper) to collect job data from XING.com. For LinkedIn jobs that require login, check out the [LinkedIn Jobs Search Scraper](https://apify.com/curious_coder/linkedin-jobs-search-scraper) for advanced search features and the [LinkedIn Jobs Scraper Unlimited](https://apify.com/curious_coder/linkedin-jobs-scraper-unlimited) for high-volume cookieless scraping. To find contact information for companies posting jobs, use the [Contact Info Finder](https://apify.com/supreme_coder/contact-info-finder) for comprehensive contact details including verified email addresses.

# How to scrape more than 1000 Linkedin jobs per search [Copy link to clipboard](https://apify.com/curious_coder/linkedin-jobs-scraper\#how-to-scrape-more-than-1000-linkedin-jobs-per-search)

Linkedin limits number of jobs per search to 1000 even though total number of jobs matching the search are far more than that. To overcome this limit you can enable "Split search urls by location" feature.

Just provide a target country and the scraper will generate multiple search urls with same filters but targeting different cities in the country. It will also ignore duplicate jobs

## How to scrape new jobs every day automatically [Copy link to clipboard](https://apify.com/curious_coder/linkedin-jobs-scraper\#how-to-scrape-new-jobs-every-day-automatically)

On Linkedin jobs search page, Select date filter (By default it is set to "Anytime") to "Last 24 hours" and fill in other required filters and copy the search URL from address bar

Then schedule this actor to run daily with copied jobs search URL as input. You don't need to generate the search URL everyday as Linkedin knows from the search url that it needs to apply last 24 hours filter

## Sample output data [Copy link to clipboard](https://apify.com/curious_coder/linkedin-jobs-scraper\#sample-output-data)

You can get the output data in any format of your preference.

Here is the sample output of this actor in json format:

```
{
	"id": "3692563200",
	"link": "https://www.linkedin.com/jobs/view/english-data-labeling-analyst-at-facebook-3692563200?refId=WG865nttvc0AIFSWNZZS8w%3D%3D&trackingId=wcG3vxpHJfGtFUkaaMVelQ%3D%3D&position=1&pageNum=0&trk=public_jobs_jserp-result_search-card",
	"title": "English Data Labeling Analyst",
	"companyName": "Facebook",
	"companyLinkedinUrl": "https://www.linkedin.com/company/facebook?trk=public_jobs_jserp-result_job-search-card-subtitle",
	"companyLogo": "https://media.licdn.com/dms/image/C4E0BAQHi-wrXiQcbxw/company-logo_100_100/0/1635988509026?e=2147483647&v=beta&t=pKAh1a653MsJvWqrqxSunoCVUALyq29eXX1oqobspnE",
	"location": "Los Angeles Metropolitan Area",
	"salaryInfo": [\
		"$17.00",\
		"$19.00"\
	],
	"postedAt": "2023-08-16",
	"benefits": [\
		"Actively Hiring"\
	],
	"descriptionHtml": "<p>APPROVED REMOTE LOCATIONS:</p><p>Los Angeles, CA, San Fransisco Bay Area, CA, San Diego, CA, New York, NY, Denver, CO, Houston, TX, Seattle, WA.</p><p><br></p><p>Summary:</p><p>The main function of a data labeling analyst is to create and manage labeling and change processes within the data management systems. The typical data labeling analyst will have experience in data quality assurance.</p><p><br></p><p>Job Responsibilities:</p><p>• Create and modify data labels ensuring compliance to all regulatory and legal requirements.</p><p>• Maintain batch records, room logs, product travelers, and inventory records.</p><p>• Label and analyze large data sets to inform product decisions.</p><p>• Asses data quality.</p><p><br></p><p>Skills:</p><p>• Ability to identify trends within large data sets.</p><p>• Excellent communication skills, verbal and written.</p><p>• Problem solving skills.</p><p>• Team oriented with attention for detail.</p><p><br></p><p>Education/Experience:</p><ul><li>• Bachelors degree in related field.</li></ul>",
	"applicantsCount": "200",
	"applyUrl": "",
	"descriptionText": "APPROVED REMOTE LOCATIONS:Los Angeles, CA, San Fransisco Bay Area, CA, San Diego, CA, New York, NY, Denver, CO, Houston, TX, Seattle, WA.Summary:The main function of a data labeling analyst is to create and manage labeling and change processes within the data management systems. The typical data labeling analyst will have experience in data quality assurance.Job Responsibilities:• Create and modify data labels ensuring compliance to all regulatory and legal requirements.• Maintain batch records, room logs, product travelers, and inventory records.• Label and analyze large data sets to inform product decisions.• Asses data quality.Skills:• Ability to identify trends within large data sets.• Excellent communication skills, verbal and written.• Problem solving skills.• Team oriented with attention for detail.Education/Experience:• Bachelors degree in related field.",
	"jobPosterName": "Andrea Cowan",
	"jobPosterTitle": "Technical Recruiter at Meta",
	"jobPosterPhoto": "https://media.licdn.com/dms/image/C5603AQErv53vemaq_A/profile-displayphoto-shrink_100_100/0/1657753132661?e=1699488000&v=beta&t=5R1WgyX-TbL6qhhsntBeR5qmjKdTL5G2l2KtroVTntM",
	"jobPosterProfileUrl": "https://ca.linkedin.com/in/andrea-cowan-458b5423b",
	"seniorityLevel": "Associate",
	"employmentType": "Contract",
	"jobFunction": "Other",
	"industries": "Retail Office Equipment",
	"companyDescription": "The Facebook company is now Meta. Meta builds technologies that help people connect, find communities, and grow businesses. When Facebook launched in 2004, it changed the way people connect. Apps like Messenger, Instagram and WhatsApp further empowered billions around the world. Now, Meta is moving beyond 2D screens toward immersive experiences like augmented and virtual reality to help build the next evolution in social technology. \n\nWe want to give people the power to build community and bring the world closer together. To do that, we ask that you help create a safe and respectful online space. These community values encourage constructive conversations on this page:\n\n• Start with an open mind. Whether you agree or disagree, engage with empathy.\n• Comments violating our Community Standards will be removed or hidden. So please treat everybody with respect. \n• Keep it constructive. Use your interactions here to learn about and grow your understanding of others.\n• Our moderators are here to uphold these guidelines for the benefit of everyone, every day. \n• If you are seeking support for issues related to your Facebook account, please reference our Help Center (https://www.facebook.com/help) or Help Community (https://www.facebook.com/help/community).\n\nFor a full listing of our jobs, visit http://www.facebookcareers.com ",
	"companyWebsite": "https://www.meta.com",
	"companyEmployeesCount": 36275
}
```

## Integrations [Copy link to clipboard](https://apify.com/curious_coder/linkedin-jobs-scraper\#integrations)

You can use [Make](https://www.make.com/en/register?pc=growthhack) to integrate Linkedin job scraper to any other SaaS platform by designing your own automation flows.

## Linkedin jobs API [Copy link to clipboard](https://apify.com/curious_coder/linkedin-jobs-scraper\#linkedin-jobs-api)

The actor stores results in a dataset. You can export data in various formats such as CSV, JSON, XLS, etc.
You can scrape and access data on demand using API. For more information, Go to [{{actorName}} API integration](https://apify.com/curious_coder/linkedin-jobs-scraper/api/endpoints) page

