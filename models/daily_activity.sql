select
    cast(initiated_at as date) as activity_date_utc,
    currency,
    count(*) as record_count,
    count(*) filter (where status = 'S') as completed_count,
    count(*) filter (where status = 'P') as pending_count,
    count(*) filter (where status = 'D') as denied_count,
    count(*) filter (where status = 'V') as reversed_count,
    coalesce(sum(amount) filter (where status = 'S'), 0)::decimal(20, 8)
        as completed_signed_amount
from {{ ref('payments') }}
group by 1, 2
