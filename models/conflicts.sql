-- Do not invent a winning value when the latest source versions disagree.
with latest as (
    select * from main.valid_records
    qualify updated_at = max(updated_at) over (partition by transaction_id, event_code)
)
select transaction_id, event_code, updated_at, count(*) as conflicting_versions
from latest
group by 1, 2, 3
having count(distinct (status, currency, amount, initiated_at)) > 1
