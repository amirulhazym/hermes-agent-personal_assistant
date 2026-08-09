#!/bin/bash
# DeepSeek balance checker - outputs formatted balance
source /home/ubuntu/.hermes/.env 2>/dev/null
json=$(curl -s "https://api.deepseek.com/user/balance" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY")

available=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print('✅ Available' if d.get('is_available') else '❌ Unavailable')")
echo "$available"

echo "$json" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for bi in d.get('balance_infos', []):
    curr = bi['currency']
    total = bi['total_balance']
    granted = bi['granted_balance']
    topped = bi['topped_up_balance']
    flag = ' ⚠️ LOW' if curr == 'CNY' and float(total) < 10.0 else ''
    if curr == 'CNY':
        print(f'🇨🇳 CNY  Total: ¥{total}  |  Granted: ¥{granted}  |  Topped Up: ¥{topped}{flag}')
    else:
        print(f'🇺🇸 USD  Total: \${total}  |  Granted: \${granted}  |  Topped Up: \${topped}')
"
