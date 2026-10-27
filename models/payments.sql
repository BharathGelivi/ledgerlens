with latest as (
    select *
    from main.valid_records
    qualify updated_at = max(updated_at) over (partition by transaction_id, event_code)
)
select * from latest
where (transaction_id, event_code) not in (
    select transaction_id, event_code from {{ ref('conflicts') }}
)
qualify row_number() over (
    partition by transaction_id, event_code order by record_hash
) = 1
