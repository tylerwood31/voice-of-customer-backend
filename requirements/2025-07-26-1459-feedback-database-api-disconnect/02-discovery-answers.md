# Discovery Answers

## Q1: Is this issue affecting the production deployment currently live for users?
**Answer:** Yes

## Q2: Should the cache refresh process run automatically without manual intervention?
**Answer:** The full table of data should update on Sundays at 11:59pm but the new records should update once per hour during business hours 9am - 9pm monday through friday.

## Q3: Do all 5,000+ records need to be immediately available after the fix?
**Answer:** Yes

## Q4: Should the system gracefully handle partial Airtable failures or network issues?
**Answer:** Yes

## Q5: Do users need real-time updates when new records are added to Airtable?
**Answer:** No - once per hour is fine