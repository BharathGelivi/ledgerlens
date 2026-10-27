with detail as (
    select currency, sum(amount) as total
    from {{ ref('payments') }} where status = 'S' group by 1
), summary as (
    select currency, sum(completed_signed_amount) as total
    from {{ ref('daily_activity') }} group by 1
)
select coalesce(d.currency, s.currency) as currency
from detail d full outer join summary s using (currency)
where coalesce(d.total, 0) <> coalesce(s.total, 0)
