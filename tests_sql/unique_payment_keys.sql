select transaction_id, event_code
from {{ ref('payments') }}
group by 1, 2 having count(*) > 1
