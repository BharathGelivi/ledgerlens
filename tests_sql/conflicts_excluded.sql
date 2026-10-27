select p.transaction_id, p.event_code
from {{ ref('payments') }} p
inner join {{ ref('conflicts') }} c using (transaction_id, event_code)
