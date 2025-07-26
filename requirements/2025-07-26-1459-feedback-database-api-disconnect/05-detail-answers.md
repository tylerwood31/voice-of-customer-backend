# Expert Detail Answers

## Q6: Should the new scheduling system extend the existing cron infrastructure in setup_cron.sh?
**Answer:** not sure

## Q7: Should the cache system automatically initialize the new database schema on startup if tables don't exist?
**Answer:** not sure

## Q8: Should failed Airtable API calls implement exponential backoff retry logic with a maximum of 3 attempts?
**Answer:** not sure

## Q9: Should the system continue serving existing cached data when new cache updates fail?
**Answer:** not sure

## Q10: Should the business hours schedule (9 AM - 9 PM Mon-Fri) use UTC time or server local time?
**Answer:** 9am - 6pm EST Mon-Fri, then full update of database Sundays at 11:59pm EST.