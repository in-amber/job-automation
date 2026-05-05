# Linkedin Jobs Scraper Input Fields

## Description

**Linkedin jobs search URLs**

`urls`

*Required*

Go to [linkedin jobs search page](https://www.linkedin.com/jobs/search/) on incognito window (to access public version), search with required filters and once you are done, copy the full URL from address bar and pass it here. You can pass multiple search URLs

Type:array

**Scrape company details**

`scrapeCompany`

*Optional*

This will require additional scraping requests for each job record and take longer to scrape

Type:boolean

Default:true

**Number of jobs needed**

`count`

*Optional*

Limit number of jobs scraped

Type:integer

Minimum:10

**Split search by city locations**

`splitByLocation`

*Optional*

Enable this to split your search by cities within a country. This helps bypass LinkedIn's 1000 job limit per search URL by creating separate searches for each city. This will overwrite the location filter in input search URLs.

Type:boolean

Default:false

**Country to split by**

`splitCountry`

*Optional*

Select the country whose cities will be used to split the search. Only used when 'Split search by city locations' is enabled. Required to when 'Split search by city locations' is enabled.

Type:string

Options:

US, CA, MX, GB, DE, FR, NL, CH, SE, NO, DK, FI, IE, ES, IT, PT, BE, AT, PL, CZ, RO, HU, GR, BG, HR, RS, UA, SK, LT, LV, EE, SI, LU, MT, IS, CY, TR, RU, GE, AM, AZ, BY, BA, XK, MD, ME, MK, AL, MC, AD, LI, SM, VA, IN, CN, JP, KR, SG, HK, TW, TH, VN, ID, MY, PH, BD, PK, LK, NP, MM, KH, KZ, UZ, KG, TJ, TM, MN, BN, MV, BT, LA, TL, AF, KP, AE, SA, IL, QA, KW, BH, OM, JO, LB, IQ, IR, PS, SY, YE, AU, NZ, FJ, PG, WS, TO, VU, SB, KI, MH, FM, PW, NR, TV, BR, AR, CO, CL, PE, EC, UY, VE, BO, PY, GY, SR, CR, PA, GT, DO, PR, JM, TT, HN, SV, NI, BS, BB, CU, HT, BZ, AG, DM, GD, LC, KN, VC, ZA, NG, KE, EG, MA, GH, ET, TZ, RW, UG, SN, TN, CI, CM, DZ, AO, MU, ZM, ZW, MZ, CD, BW, NA, MG, LY, SD, SS, SO, ML, GA, BJ, BF, MW, NE, TD, SL, LR, ER, GM, GN, GW, TG, MR, SZ, LS, DJ, CG, CF, BI, CV, KM, GQ, ST, SC
