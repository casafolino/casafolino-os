#!/usr/bin/env python3
"""Generate Arpaia reconciliation audit files."""
import csv
import os
from datetime import date

OUT = os.path.dirname(os.path.abspath(__file__))

# ── D2: Fatture/NC aperte ──────────────────────────────────────────
# id|numero|data|riferimento|tipo|totale|residuo|stato_pagamento
RAW_D2 = """10746|ACQ/2023/12/0001|2023-12-31|2143/FN|in_invoice|18.29|0.00|not_paid
10807|ACQ/2023/12/0002|2023-12-31|7409|in_invoice|202.78|0.00|not_paid
10745|ACQ/2024/01/0016|2024-01-31|134/FN|in_invoice|106.28|0.00|not_paid
10240|ACQ/2024/02/0015|2024-02-29|381/FN|in_invoice|41.25|0.00|not_paid
10747|ACQ/2024/02/0016|2024-02-29|417/FN|in_invoice|47.82|0.00|not_paid
10744|ACQ/2024/02/0017|2024-02-29|446/FN|in_invoice|90.86|0.00|not_paid
10826|ACQ/2024/02/0018|2024-02-29|669|in_invoice|95.65|0.00|not_paid
10282|ACQ/2024/02/0019|2024-02-29|792|in_invoice|272.26|0.00|not_paid
10827|ACQ/2024/02/0020|2024-02-29|921|in_invoice|69.34|0.00|not_paid
10299|ACQ/2024/03/0025|2024-03-31|1174|in_invoice|222.86|0.00|not_paid
10316|ACQ/2024/03/0026|2024-03-31|1244|in_invoice|105.21|0.00|not_paid
10688|ACQ/2024/05/0002|2024-05-31|2545|in_invoice|142.52|0.00|not_paid
10618|ACQ/2024/05/0003|2024-05-31|880/FN|in_invoice|50.22|0.00|not_paid
10715|ACQ/2024/06/0025|2024-06-30|2775|in_invoice|143.47|0.00|not_paid
10717|ACQ/2024/06/0026|2024-06-30|2886|in_invoice|83.22|0.00|not_paid
10614|ACQ/2024/06/0027|2024-06-30|938/FN|in_invoice|107.61|0.00|not_paid
10616|ACQ/2024/06/0028|2024-06-30|953/FN|in_invoice|23.18|0.00|not_paid
10615|ACQ/2024/07/0030|2024-07-31|1103/FN|in_invoice|95.65|0.00|not_paid
10617|ACQ/2024/07/0031|2024-07-31|1112/FN|in_invoice|23.31|0.00|not_paid
10613|ACQ/2024/07/0032|2024-07-31|1158/FN|in_invoice|86.08|0.00|not_paid
10612|ACQ/2024/07/0033|2024-07-31|1169/FN|in_invoice|105.21|0.00|not_paid
10701|ACQ/2024/07/0034|2024-07-31|3477|in_invoice|257.06|0.00|not_paid
10608|ACQ/2024/07/0035|2024-07-31|3484|in_invoice|390.84|0.00|not_paid
10700|ACQ/2024/07/0036|2024-07-31|3554|in_invoice|262.32|0.00|not_paid
10716|ACQ/2024/07/0037|2024-07-31|3621|in_invoice|143.47|0.00|not_paid
10658|ACQ/2024/07/0038|2024-07-31|3654|in_invoice|271.78|0.00|not_paid
10610|ACQ/2024/07/0039|2024-07-31|3715|in_invoice|71.02|0.00|not_paid
10719|ACQ/2024/07/0040|2024-07-31|3816|in_invoice|71.02|0.00|not_paid
10718|ACQ/2024/07/0041|2024-07-31|3902|in_invoice|71.02|0.00|not_paid
10662|ACQ/2024/08/0022|2024-08-31|4349|in_invoice|673.22|0.00|not_paid
10484|ACQ/2024/09/0008|2024-09-30|1523/FN|in_invoice|129.12|0.00|not_paid
10549|ACQ/2024/09/0009|2024-09-30|4977|in_invoice|143.47|0.00|not_paid
10478|ACQ/2024/09/0010|2024-09-30|5067|in_invoice|333.33|0.00|not_paid
10541|ACQ/2024/09/0011|2024-09-30|5167|in_invoice|276.66|0.00|not_paid
9858|ACQ/2024/10/0024|2024-10-31|1662/FN|in_invoice|76.52|0.00|not_paid
10482|ACQ/2024/10/0025|2024-10-31|1663/FN|in_invoice|62.17|0.00|not_paid
10486|ACQ/2024/10/0026|2024-10-31|1868/FN|in_invoice|74.60|0.00|not_paid
9852|ACQ/2024/10/0027|2024-10-31|5613|in_invoice|1039.97|0.00|not_paid
10483|RACQ/2024/10/0003|2024-10-31|10/NCN|in_refund|76.52|76.52|not_paid
10485|ACQ/2024/11/0030|2024-11-30|2002/FN|in_invoice|47.82|0.00|not_paid
10480|ACQ/2024/11/0031|2024-11-30|2035/FN|in_invoice|70.06|0.00|not_paid
9855|ACQ/2024/11/0032|2024-11-30|6577|in_invoice|299.85|0.00|not_paid
10540|ACQ/2024/11/0033|2024-11-30|6707|in_invoice|171.21|0.00|not_paid
9851|ACQ/2024/11/0034|2024-11-30|6953|in_invoice|1555.61|0.00|not_paid
9850|ACQ/2024/11/0035|2024-11-30|7043|in_invoice|4648.35|0.00|not_paid
9864|RACQ/2024/12/0002|2024-12-31|2145|in_refund|18.30|18.30|not_paid
9861|RACQ/2024/12/0003|2024-12-31|2146|in_refund|46.97|46.97|not_paid
10121|ACQ/2025/01/0024|2025-01-31|175/FN|in_invoice|71.74|0.00|not_paid
10114|ACQ/2025/01/0025|2025-01-31|24/FN|in_invoice|71.74|0.00|not_paid
10172|ACQ/2025/01/0026|2025-01-31|523|in_invoice|237.68|0.00|not_paid
10113|ACQ/2025/01/0027|2025-01-31|578|in_invoice|143.47|0.00|not_paid
10120|RACQ/2025/01/0002|2025-01-31|2/NCN|in_refund|62.17|62.17|not_paid
10115|ACQ/2025/02/0015|2025-02-28|242/FN|in_invoice|49.49|0.00|not_paid
10122|ACQ/2025/02/0016|2025-02-28|333/FN|in_invoice|21.13|0.00|not_paid
10116|ACQ/2025/02/0017|2025-02-28|356/FN|in_invoice|95.65|1.44|not_paid
10173|ACQ/2025/02/0018|2025-02-28|645|in_invoice|243.19|0.00|not_paid
10174|ACQ/2025/02/0019|2025-02-28|904|in_invoice|247.24|247.24|not_paid
10125|RACQ/2025/02/0001|2025-02-28|188|in_refund|243.39|243.39|not_paid
10194|ACQ/2025/03/0015|2025-03-31|1025|in_invoice|71.02|0.00|not_paid
10176|ACQ/2025/03/0016|2025-03-31|1162|in_invoice|219.74|219.74|not_paid
10193|ACQ/2025/03/0017|2025-03-31|1225|in_invoice|239.12|0.00|not_paid
10175|ACQ/2025/03/0018|2025-03-31|1293|in_invoice|171.92|0.00|not_paid
10163|ACQ/2025/03/0019|2025-03-31|1322|in_invoice|242.58|0.00|not_paid
10171|ACQ/2025/03/0020|2025-03-31|1337|in_invoice|476.09|0.00|not_paid
10119|ACQ/2025/03/0021|2025-03-31|382/FN|in_invoice|47.82|0.00|not_paid
10124|ACQ/2025/03/0022|2025-03-31|386/FN|in_invoice|137.25|0.00|not_paid
10123|ACQ/2025/03/0023|2025-03-31|410/FN|in_invoice|152.16|152.16|not_paid
10117|ACQ/2025/03/0024|2025-03-31|429/FN|in_invoice|95.65|0.00|not_paid
10118|ACQ/2025/03/0025|2025-03-31|439/FN|in_invoice|68.65|0.00|not_paid
12039|ACQ/2025/03/0067|2025-03-31|1322|in_invoice|242.58|0.00|not_paid
11392|ACQ/2025/04/0033|2025-04-30|629/FN|in_invoice|263.03|0.00|not_paid
11395|ACQ/2025/04/0050|2025-04-30|1606|in_invoice|214.49|0.00|not_paid
11394|ACQ/2025/04/0063|2025-04-30|551/FN|in_invoice|10.64|0.00|not_paid
11393|ACQ/2025/04/0064|2025-04-30|546/FN|in_invoice|21.13|0.00|not_paid
11837|ACQ/2025/05/0046|2025-05-31|2313|in_invoice|142.03|142.03|not_paid
11835|ACQ/2025/05/0049|2025-05-31|718/FN|in_invoice|74.73|74.73|not_paid
11836|ACQ/2025/05/0050|2025-05-31|737/FN|in_invoice|210.43|210.43|not_paid
12049|ACQ/2025/06/0063|2025-06-23|2585|in_invoice|104.36|104.36|not_paid
12051|ACQ/2025/06/0064|2025-06-23|2642|in_invoice|262.32|262.32|not_paid
12050|ACQ/2025/06/0065|2025-06-23|841/FN|in_invoice|71.02|71.02|not_paid
12730|ACQ/2025/06/0072|2025-06-26|862/FN|in_invoice|304.16|304.16|not_paid
12868|ACQ/2025/06/0087|2025-06-30|901/FN|in_invoice|414.62|414.62|not_paid
12924|ACQ/2025/07/0005|2025-07-08|928/FN|in_invoice|405.06|405.06|not_paid
13106|ACQ/2025/07/0023|2025-07-21|3328|in_invoice|464.84|464.84|not_paid
13147|ACQ/2025/07/0029|2025-07-25|1018/FN|in_invoice|213.06|0.00|not_paid
13193|ACQ/2025/07/0045|2025-07-29|1040/FN|in_invoice|11.96|0.25|not_paid
13542|ACQ/2025/08/0036|2025-08-18|3942|in_invoice|5517.48|16.20|not_paid
13540|ACQ/2025/08/0037|2025-08-18|4145|in_invoice|281.82|281.82|not_paid
13541|RACQ/2025/08/0003|2025-08-18|1216|in_refund|648.38|648.38|not_paid
13681|ACQ/2025/08/0057|2025-08-26|1194/FN|in_invoice|97.20|2.59|not_paid
13680|ACQ/2025/08/0059|2025-08-26|4206|in_invoice|142.03|0.00|not_paid
13754|ACQ/2025/08/0064|2025-08-29|1204/FN|in_invoice|8.37|2.74|not_paid
13870|RACQ/2025/08/0002|2025-08-31|1369|in_refund|348.92|348.92|not_paid
13925|ACQ/2025/09/0023|2025-09-10|4570|in_invoice|837.41|2.59|not_paid
13924|ACQ/2025/09/0024|2025-09-10|4606|in_invoice|1121.08|0.00|not_paid
14034|ACQ/2025/09/0054|2025-09-19|4788|in_invoice|123.74|123.74|not_paid
14032|ACQ/2025/09/0056|2025-09-19|4847|in_invoice|310.14|0.00|not_paid
14033|ACQ/2025/09/0057|2025-09-19|4836|in_invoice|355.09|0.00|not_paid
14078|ACQ/2025/09/0061|2025-09-23|4895|in_invoice|528.70|0.00|not_paid
14150|ACQ/2025/09/0076|2025-09-29|4967|in_invoice|213.06|0.00|not_paid
14193|ACQ/2025/09/0079|2025-09-30|5099|in_invoice|1197.59|0.00|not_paid
14194|ACQ/2025/09/0080|2025-09-30|5103|in_invoice|913.51|913.51|not_paid
14192|RACQ/2025/09/0001|2025-09-30|1553|in_refund|170.97|170.97|not_paid
14435|ACQ/2025/10/0033|2025-10-22|1544/FN|in_invoice|63.38|0.00|not_paid
15474|ACQ/2025/10/0048|2025-10-28|1583/FN|in_invoice|213.06|213.06|not_paid
15925|ACQ/2025/10/0072|2025-10-31|1665/FN|in_invoice|74.73|0.00|not_paid
15923|ACQ/2025/10/0073|2025-10-31|5904|in_invoice|243.90|0.00|not_paid
15922|ACQ/2025/10/0074|2025-10-31|5935|in_invoice|123.74|0.00|not_paid
15929|ACQ/2025/10/0078|2025-10-31|5873|in_invoice|1107.46|0.00|not_paid
15934|ACQ/2025/10/0082|2025-10-31|5801|in_invoice|1192.09|1192.09|not_paid
15950|ACQ/2025/10/0083|2025-10-31|1603/FN|in_invoice|0.00|0.00|not_paid
15924|RACQ/2025/10/0002|2025-10-31|1812|in_refund|70.76|70.76|not_paid
15935|RACQ/2025/10/0003|2025-10-31|1790|in_refund|1098.46|1098.46|not_paid
15876|ACQ/2025/11/0030|2025-11-22|1766/FN|in_invoice|14.95|0.00|not_paid
15887|ACQ/2025/11/0036|2025-11-22|6144|in_invoice|142.03|142.03|not_paid
15896|ACQ/2025/11/0048|2025-11-22|1684/FN|in_invoice|284.08|0.00|not_paid
15900|ACQ/2025/11/0050|2025-11-22|6055|in_invoice|1674.88|1674.88|not_paid
15889|ACQ/2025/11/0051|2025-11-22|6107|in_invoice|213.41|124.74|not_paid
15886|ACQ/2025/11/0052|2025-11-22|6157|in_invoice|509.33|509.33|not_paid
15888|RACQ/2025/11/0003|2025-11-22|1874|in_refund|355.09|355.09|not_paid
15999|ACQ/2025/11/0046|2025-11-27|6600|in_invoice|985.17|64.88|not_paid
16038|ACQ/2025/11/0020|2025-11-30|6930|in_invoice|836.99|0.00|not_paid
16028|ACQ/2025/11/0021|2025-11-30|6932|in_invoice|1238.72|432.30|not_paid
16007|ACQ/2025/11/0022|2025-11-30|6690|in_invoice|478.24|0.00|not_paid
16017|ACQ/2025/11/0023|2025-11-30|6827|in_invoice|816.67|0.00|not_paid
16018|RACQ/2025/11/0002|2025-11-30|2004|in_refund|174.46|174.46|not_paid
16429|ACQ/2025/12/0024|2025-12-11|7097|in_invoice|258.25|0.00|not_paid
16430|ACQ/2025/12/0025|2025-12-11|7068|in_invoice|143.47|0.00|not_paid
16469|ACQ/2025/12/0020|2025-12-12|1919/FN|in_invoice|205.64|0.00|not_paid
16836|ACQ/2025/12/0031|2025-12-15|7213|in_invoice|836.99|0.00|not_paid
17087|ACQ/2025/12/0067|2025-12-29|2091/FN|in_invoice|243.90|0.00|not_paid
17085|ACQ/2025/12/0068|2025-12-29|7530|in_invoice|401.72|0.00|not_paid
17086|ACQ/2025/12/0069|2025-12-29|7685|in_invoice|143.47|0.00|not_paid
17088|RACQ/2025/12/0001|2025-12-29|2152|in_refund|239.73|239.73|not_paid
17107|ACQ/2025/12/0066|2025-12-30|7760|in_invoice|837.41|0.00|not_paid
17217|ACQ/2025/12/0088|2025-12-31|7770|in_invoice|502.15|23.91|not_paid
17339|ACQ/2025/12/0097|2025-12-31|7783|in_invoice|2035.07|2035.07|not_paid
17611|ACQ/2026/01/0070|2026-01-31|508|in_invoice|2349.41|275.38|not_paid
17612|RACQ/2026/01/0002|2026-01-31|144|in_refund|244.29|244.29|not_paid
17682|ACQ/2026/02/0018|2026-02-12|231/FN|in_invoice|123.74|0.00|not_paid
17684|ACQ/2026/02/0019|2026-02-12|214/FN|in_invoice|41.85|0.00|not_paid
18422|ACQ/2026/03/0022|2026-03-31|1481|in_invoice|3358.53|3358.53|not_paid
18392|ACQ/2026/03/0024|2026-03-31|1710|in_invoice|1662.37|1662.37|not_paid
18393|ACQ/2026/03/0025|2026-03-31|495|in_invoice|413.10|413.10|not_paid
18423|RACQ/2026/03/0001|2026-03-31|405|in_refund|280.60|280.60|not_paid
18492|ACQ/2026/04/0001|2026-04-14|1756|in_invoice|298.22|298.22|not_paid
43190|ACQ/2026/04/0044|2026-04-30|1947|in_invoice|1340.63|1340.63|not_paid
43220|ACQ/2026/04/0045|2026-04-30|2103|in_invoice|299.95|299.95|not_paid
43221|ACQ/2026/04/0046|2026-04-30|620/FN|in_invoice|3.77|3.77|not_paid
43234|ACQ/2026/04/0055|2026-04-30|2121|in_invoice|62.27|62.27|not_paid
43191|RACQ/2026/04/0002|2026-04-30|574|in_refund|90.89|90.89|not_paid"""

# ── D3: BSL partner_id=4956 non riconciliati ──────────────────────
# id|data|journal|journal_id|descrizione|rif|debit|credit|balance|reconciled|full_reconcile_id
RAW_D3 = """132558|2025-08-06|REVOLUT CASAFOLINO|13|Open balance of -5,501.08 €|68933abe-044a-ad2b-a347-dd19179426d5|5099.36|0.00|5099.36|f|
132557|2025-08-06|REVOLUT CASAFOLINO|13|A Arpaia spa | Vs ft|68933abe-044a-ad2b-a347-dd19179426d5|401.72|0.00|401.72|f|
132556|2025-08-06|REVOLUT CASAFOLINO|13|A Arpaia spa | Vs ft|68933abe-044a-ad2b-a347-dd19179426d5|0.00|5501.08|-5501.08|f|
132133|2025-12-09|REVOLUT CASAFOLINO|13|Open balance of -843.46 €|6938a74c-e494-ae54-ad6f-8e04a9f67761|441.74|0.00|441.74|f|
132131|2025-12-09|REVOLUT CASAFOLINO|13|A Arpaia spa | Vs ft|6938a74c-e494-ae54-ad6f-8e04a9f67761|0.00|843.46|-843.46|f|
132132|2025-12-09|REVOLUT CASAFOLINO|13|A Arpaia spa | Vs ft|6938a74c-e494-ae54-ad6f-8e04a9f67761|401.72|0.00|401.72|f|
130566|2026-03-24|REVOLUT CASAFOLINO|13|A Arpaia spa | Vs ft|69c2a2b4-51f0-ab02-b0b5-4fc13e81ce64|0.00|401.72|-401.72|f|
130564|2026-04-09|REVOLUT CASAFOLINO|13|Arpaia Spa|69d7ce7b-772a-a8d4-8d88-7f75d7fd76ae|0.00|21.40|-21.40|f|"""

# ── D4: BSL orfani (outflow lines only, balance < 0) ─────────────
# id|data|descrizione|ref|importo_pagamento
RAW_D4_OUTFLOWS = """115693|2025-04-24|Arpaia Spa|6809ea44-b6ed-a833-bf04-92d0367a01cc|263.03
115927|2025-05-22|Arpaia Spa|682ec8bf-b1b3-a342-a281-79c98140c5cd|142.03
116177|2025-06-09|Arpaia Spa|6846870d-404e-af4a-bf4e-a801f6e7af19|104.36
116185|2025-06-10|Arpaia Spa|68484b32-de21-a243-81ad-fada18e57223|262.31
116255|2025-06-19|Arpaia Spa|6853cc85-e4df-a854-9418-e6e527838706|304.16
116259|2025-06-19|Arpaia Spa|6853cbbe-833c-a8a4-b316-2145e9778d12|71.02
116397|2025-06-25|Arpaia Spa|685ba587-6f89-a0e4-8926-2a91793bde63|414.63
116581|2025-07-10|Arpaia Spa|686fbc87-41f7-a7fb-86c8-4a54fc4785af|464.84
116579|2025-07-10|Arpaia Spa|686fb862-e13f-af7d-a409-ebfb6f7d9aa1|358.09
116685|2025-07-16|Arpaia Spa|68775c75-8fb2-ab39-8f69-d730020a8650|213.06
116737|2025-07-21|Arpaia Spa|687e1afa-58a6-a3a0-aa58-35f6f9f72292|11.71
117199|2025-09-02|Arpaia Spa|68b7039d-001a-ae82-abc8-ba36320f98e7|1118.53
117293|2025-09-10|Arpaia Spa|68c1828a-03bc-ac5a-b0b4-bc8f1c79f7e0|492.16
117377|2025-09-12|Arpaia Spa|68c427f9-70b7-aa33-aa68-80ae7487305e|310.14
117367|2025-09-12|Arpaia Spa|68c3d496-aea7-a728-a43f-fd5569580eb4|355.09
117397|2025-09-16|Arpaia Spa|68c925a5-46a4-ad74-aa1c-b64bec7e88bb|528.70
117511|2025-09-24|Arpaia Spa|68d39eec-dcad-af60-a39d-b91c2546ece2|78.08
117509|2025-09-24|Arpaia Spa|68d39e5c-de9e-afcd-9e16-109ef74d2416|1116.97
117517|2025-09-24|Arpaia Spa|68d39e86-1685-aa11-9173-a97cb232a167|213.06
117513|2025-09-24|Arpaia Spa|68d3b67d-8ab2-a0de-830a-b68cd0901606|740.00
117741|2025-10-14|Arpaia Spa|68ee62b2-a821-a492-86be-0a11adb22ef9|63.38
117829|2025-10-22|Arpaia Spa|68f89def-1cfc-a36a-afec-b6972fc249a1|26.41
117821|2025-10-22|Arpaia Spa|68f89e24-d643-a10c-b467-cb22df731bf7|213.06
117881|2025-10-28|Arpaia Spa|690097ed-fa10-a9a4-8a66-899c2cfb4cc8|94.61
117879|2025-10-28|Arpaia Spa|6900982e-07b7-a5c0-bd39-07970d88bc27|1107.46
117911|2025-10-29|Arpaia Spa|69023ebc-81e4-acfb-85eb-f822973b7c58|123.74
117903|2025-10-29|Arpaia Spa|690237e5-54cf-a5f4-a706-12f185578b41|74.73
118265|2025-11-25|Arpaia Spa|6925b9a8-8ea5-a9d0-bb23-9734b823ae0f|1669.69
118293|2025-12-03|Arpaia Spa|692ff0c9-fb39-a0c8-a10c-34bf3b208e9f|258.25
118687|2025-12-22|Arpaia Spa|694905dc-84a2-a3da-861f-f1495f3211b4|243.90
118705|2025-12-22|Arpaia Spa|69490510-f3d0-ac4c-8056-c1a35f24dba3|243.90
118689|2025-12-22|Arpaia Spa|694905bf-d7e5-a154-9969-c96146082814|205.64
118691|2025-12-22|Arpaia Spa|6949059b-ae53-a9b1-be63-bb4d3b30a653|14.95
118697|2025-12-22|Arpaia Spa|69490548-a744-ae05-b717-517fcdf9b1b0|401.72
118699|2025-12-22|Arpaia Spa|6949052e-cc09-acb2-9c53-e9487d52f7fc|213.41
118695|2025-12-22|Arpaia Spa|69490562-b990-a641-9da4-14e6b82d6fee|143.47
118685|2025-12-22|Arpaia Spa|6949062a-bdc7-a2fd-8cd4-2e030bdd338a|142.03
118693|2025-12-22|Arpaia Spa|6949057e-aba7-a088-afdc-2a8c16571742|284.08
118739|2025-12-23|Arpaia Spa|694abcca-6d0b-aad5-bde7-6106b5319760|834.82
118791|2025-12-29|Arpaia Spa|695284bd-26a8-aaf7-b924-f94b28f4674e|502.14
118807|2025-12-30|Arpaia Spa|69539850-78bb-a4ae-b9c5-9ad28caab50a|2035.07
119193|2026-01-27|Arpaia Spa|6978c569-6626-acd8-920f-ebf934e1d083|2074.03
119525|2026-03-17|Arpaia Spa|69b902fe-5fcd-ac3a-b337-c60a6c3c67d3|48.00
119549|2026-03-18|Arpaia Spa|69ba713b-a2ca-a936-90a8-0fdf5f52f3e6|985.17
119563|2026-03-18|Arpaia Spa|69ba716f-3643-adba-9167-da3a722617c7|478.24
119559|2026-03-18|Arpaia Spa|69ba71c8-e61b-a80c-8fca-231dd90a744a|41.85
119561|2026-03-18|Arpaia Spa|69ba718e-37ff-a399-98df-781837d3a070|143.47
119557|2026-03-18|Arpaia Spa|69ba71ed-8385-ac9e-ba7b-56b00f9d40dd|123.74
119565|2026-03-18|Arpaia Spa|69ba70b1-96c1-a227-b61b-63a2639132af|3077.93
119825|2026-03-31|Arpaia Spa|69cbdf64-df1f-a983-9fd2-9286230e1aad|632.11
119835|2026-03-31|Arpaia Spa|69cbde82-274d-ad4a-8c51-dc8b8175676d|174.46
119823|2026-03-31|Arpaia Spa|69cbdea8-86a1-a7f4-8a66-e98ca577b849|239.73
119817|2026-03-31|Arpaia Spa|69cbde4b-db81-a65e-8ffc-85f672d2f1dd|843.46
119819|2026-03-31|Arpaia Spa|69cbde63-2acf-ad6b-8fbb-f9076aab2a5b|70.76
119937|2026-04-07|Arpaia Spa|69d4b9b9-5c78-af56-a8d0-3bb733ac16f7|298.22"""


def parse_d2():
    rows = []
    for line in RAW_D2.strip().split('\n'):
        parts = line.split('|')
        rows.append({
            'id': int(parts[0]),
            'numero': parts[1],
            'data': parts[2],
            'riferimento': parts[3],
            'tipo': parts[4],
            'totale': float(parts[5]),
            'residuo': float(parts[6]),
            'stato_pagamento': parts[7],
        })
    return rows


def parse_d3():
    rows = []
    for line in RAW_D3.strip().split('\n'):
        # Split from right to handle | in description field
        # Last 5 fields: debit|credit|balance|reconciled|full_reconcile_id
        rparts = line.rsplit('|', 5)
        left = rparts[0]  # id|data|journal|journal_id|descrizione|riferimento
        lparts = left.split('|', 5)  # split first 5 pipes from left
        # lparts: [id, data, journal, journal_id, descrizione_with_possible_pipes, riferimento]
        # But riferimento is last in lparts - we need to extract it
        # Actually: id|data|journal|journal_id|desc...|ref = 6 minimum parts
        # desc may contain |, so split left into first 4 + rest, then rsplit rest to get ref
        lparts2 = left.split('|', 4)  # [id, data, journal, journal_id, desc_and_ref]
        desc_ref = lparts2[4]
        # ref is UUID-like, always last segment
        dr_parts = desc_ref.rsplit('|', 1)
        desc = dr_parts[0]
        ref = dr_parts[1] if len(dr_parts) > 1 else ''

        rows.append({
            'id': int(lparts2[0]),
            'data': lparts2[1],
            'journal': lparts2[2],
            'journal_id': int(lparts2[3]),
            'descrizione': desc,
            'riferimento': ref,
            'debit': float(rparts[1]),
            'credit': float(rparts[2]),
            'balance': float(rparts[3]),
        })
    return rows


def parse_d4():
    rows = []
    for line in RAW_D4_OUTFLOWS.strip().split('\n'):
        parts = line.split('|')
        rows.append({
            'id': int(parts[0]),
            'data': parts[1],
            'descrizione': parts[2],
            'riferimento': parts[3],
            'importo': float(parts[4]),
        })
    return rows


def write_csv(filename, headers, rows):
    path = os.path.join(OUT, filename)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=headers, delimiter=';')
        w.writeheader()
        w.writerows(rows)
    print(f"  -> {filename}: {len(rows)} righe")


def find_matches(invoices, payments, tol=0.01):
    """Find 1:1 matches between payments and invoices/NC by amount."""
    matches = []
    used_inv = set()

    for p in payments:
        amt = p['importo']
        candidates = []
        for inv in invoices:
            if inv['id'] in used_inv:
                continue
            res = inv['residuo']
            if res <= 0:
                continue
            if abs(amt - res) <= tol:
                candidates.append(inv)

        if len(candidates) == 1:
            inv = candidates[0]
            used_inv.add(inv['id'])
            matches.append({
                'bsl_id': p['id'],
                'bsl_data': p['data'],
                'bsl_importo': p['importo'],
                'bsl_tipo': p.get('tipo', 'orfano'),
                'fattura_id': inv['id'],
                'fattura_numero': inv['numero'],
                'fattura_ref': inv['riferimento'],
                'fattura_residuo': inv['residuo'],
                'differenza': round(p['importo'] - inv['residuo'], 2),
                'tipo_match': '1:1 esatto',
            })
        elif len(candidates) > 1:
            # pick closest date
            inv = candidates[0]
            used_inv.add(inv['id'])
            matches.append({
                'bsl_id': p['id'],
                'bsl_data': p['data'],
                'bsl_importo': p['importo'],
                'bsl_tipo': p.get('tipo', 'orfano'),
                'fattura_id': inv['id'],
                'fattura_numero': inv['numero'],
                'fattura_ref': inv['riferimento'],
                'fattura_residuo': inv['residuo'],
                'differenza': round(p['importo'] - inv['residuo'], 2),
                'tipo_match': f'1:1 esatto (ambiguo, {len(candidates)} candidati)',
            })
    return matches, used_inv


def find_composite_matches(invoices, ncs, payments, used_inv, tol=0.01):
    """Try BSL = invoice - NC combinations."""
    matches = []
    for p in payments:
        amt = p['importo']
        # Try each invoice + one NC
        for inv in invoices:
            if inv['id'] in used_inv or inv['residuo'] <= 0:
                continue
            for nc in ncs:
                if nc['id'] in used_inv or nc['residuo'] <= 0:
                    continue
                net = inv['residuo'] - nc['residuo']
                if net > 0 and abs(amt - net) <= tol:
                    used_inv.add(inv['id'])
                    used_inv.add(nc['id'])
                    matches.append({
                        'bsl_id': p['id'],
                        'bsl_data': p['data'],
                        'bsl_importo': p['importo'],
                        'bsl_tipo': p.get('tipo', 'orfano'),
                        'fattura_id': inv['id'],
                        'fattura_numero': inv['numero'],
                        'fattura_ref': inv['riferimento'],
                        'fattura_residuo': inv['residuo'],
                        'differenza': round(amt - net, 2),
                        'tipo_match': f'composto: ft {inv["numero"]} - NC {nc["numero"]} (NC ref {nc["riferimento"]}, {nc["residuo"]:.2f}€)',
                    })
                    break
    return matches


def main():
    d2 = parse_d2()
    d3 = parse_d3()
    d4 = parse_d4()

    invoices = [r for r in d2 if r['tipo'] == 'in_invoice']
    ncs = [r for r in d2 if r['tipo'] == 'in_refund']

    inv_count = len(invoices)
    nc_count = len(ncs)
    inv_total = sum(r['totale'] for r in invoices)
    nc_total = sum(r['totale'] for r in ncs)
    inv_residuo = sum(r['residuo'] for r in invoices)
    nc_residuo = sum(r['residuo'] for r in ncs)
    residuo_netto = inv_residuo - nc_residuo

    # Fatture con residuo 0 ma not_paid
    inv_zero_residuo = [r for r in invoices if r['residuo'] == 0.0]
    inv_with_residuo = [r for r in invoices if r['residuo'] > 0.0]
    nc_with_residuo = [r for r in ncs if r['residuo'] > 0.0]

    # BSL D3: outflow lines (balance < 0)
    d3_outflows = [r for r in d3 if r['balance'] < 0]
    d3_total_outflow = sum(abs(r['balance']) for r in d3_outflows)

    # D4 totals
    d4_total = sum(r['importo'] for r in d4)

    total_payments = d3_total_outflow + d4_total

    # ── Prepare payment list for matching ──
    all_payments = []
    for r in d3_outflows:
        all_payments.append({
            'id': r['id'],
            'data': r['data'],
            'importo': abs(r['balance']),
            'descrizione': r['descrizione'],
            'tipo': 'partner_tagged',
        })
    for r in d4:
        all_payments.append({
            'id': r['id'],
            'data': r['data'],
            'importo': r['importo'],
            'descrizione': r['descrizione'],
            'tipo': 'orfano',
        })

    # ── Matching ──
    matches_1to1, used_inv = find_matches(d2, all_payments)
    matches_comp = find_composite_matches(invoices, ncs, all_payments, used_inv)
    all_matches = matches_1to1 + matches_comp

    matched_payment_ids = {m['bsl_id'] for m in all_matches}
    unmatched_payments = [p for p in all_payments if p['id'] not in matched_payment_ids]
    unmatched_inv = [r for r in d2 if r['id'] not in used_inv and r['residuo'] > 0]

    matched_amount = sum(m['bsl_importo'] for m in all_matches)
    unmatched_payment_amount = sum(p['importo'] for p in unmatched_payments)
    unmatched_inv_residuo = sum(r['residuo'] for r in unmatched_inv if r['tipo'] == 'in_invoice')
    unmatched_nc_residuo = sum(r['residuo'] for r in unmatched_inv if r['tipo'] == 'in_refund')

    # ── CSV files ──
    print("Generazione CSV...")

    # 01-totali.csv
    write_csv('01-totali.csv', ['voce', 'valore'], [
        {'voce': 'Fatture aperte (n)', 'valore': inv_count},
        {'voce': 'Note credito aperte (n)', 'valore': nc_count},
        {'voce': 'Totale lordo fatture', 'valore': f"{inv_total:.2f}"},
        {'voce': 'Totale lordo NC', 'valore': f"{nc_total:.2f}"},
        {'voce': 'Residuo fatture', 'valore': f"{inv_residuo:.2f}"},
        {'voce': 'Residuo NC', 'valore': f"{nc_residuo:.2f}"},
        {'voce': 'Residuo netto (ft - NC)', 'valore': f"{residuo_netto:.2f}"},
        {'voce': 'Fatture residuo=0 ma not_paid (n)', 'valore': len(inv_zero_residuo)},
        {'voce': 'BSL partner-tagged outflows', 'valore': f"{d3_total_outflow:.2f}"},
        {'voce': 'BSL orfani outflows', 'valore': f"{d4_total:.2f}"},
        {'voce': 'Totale pagamenti identificabili', 'valore': f"{total_payments:.2f}"},
        {'voce': 'Match trovati (n)', 'valore': len(all_matches)},
        {'voce': 'Match importo', 'valore': f"{matched_amount:.2f}"},
        {'voce': 'Pagamenti senza match', 'valore': f"{unmatched_payment_amount:.2f}"},
        {'voce': 'GAP = residuo_netto - pagamenti', 'valore': f"{residuo_netto - total_payments:.2f}"},
    ])

    # 02-fatture-aperte.csv
    write_csv('02-fatture-aperte.csv',
              ['id', 'numero', 'data', 'riferimento', 'tipo', 'totale', 'residuo', 'stato_pagamento'],
              d2)

    # 03-bsl-arpaia.csv (partner-tagged)
    d3_csv = []
    for r in d3:
        d3_csv.append({
            'id': r['id'],
            'data': r['data'],
            'journal': r['journal'],
            'descrizione': r['descrizione'],
            'riferimento': r['riferimento'],
            'dare': f"{r['debit']:.2f}",
            'avere': f"{r['credit']:.2f}",
            'saldo': f"{r['balance']:.2f}",
        })
    write_csv('03-bsl-arpaia.csv',
              ['id', 'data', 'journal', 'descrizione', 'riferimento', 'dare', 'avere', 'saldo'],
              d3_csv)

    # 04-bsl-orfani.csv
    d4_csv = []
    for r in d4:
        d4_csv.append({
            'id': r['id'],
            'data': r['data'],
            'descrizione': r['descrizione'],
            'riferimento': r['riferimento'],
            'importo': f"{r['importo']:.2f}",
        })
    write_csv('04-bsl-orfani.csv',
              ['id', 'data', 'descrizione', 'riferimento', 'importo'],
              d4_csv)

    # 05-match-candidati.csv
    write_csv('05-match-candidati.csv',
              ['bsl_id', 'bsl_data', 'bsl_importo', 'bsl_tipo', 'fattura_id', 'fattura_numero',
               'fattura_ref', 'fattura_residuo', 'differenza', 'tipo_match'],
              all_matches)

    # ── report.md ──
    print("Generazione report.md...")
    gap = residuo_netto - total_payments

    report = f"""# Audit Riconciliazione Arpaia spa (partner_id=4956)

**Data audit**: 2026-05-15
**Database**: folinofood (produzione)
**Operazioni eseguite**: solo SELECT (read-only)

---

## Discordanze principali

| Voce | Importo |
|------|---------|
| Residuo netto fatture (ft − NC) | **{residuo_netto:,.2f} €** |
| Pagamenti bancari identificabili | **{total_payments:,.2f} €** |
| **GAP (residuo − pagamenti)** | **{gap:,.2f} €** |

### Interpretazione GAP

Il gap è **negativo ({gap:,.2f} €)**: i pagamenti Revolut superano il residuo fatture di **{abs(gap):,.2f} €**.

**Cause probabili**:
1. **{len(inv_zero_residuo)} fatture con residuo=0 ma payment_state='not_paid'** → già chiuse contabilmente (via riconciliazione manuale o journal entry) ma stato pagamento non aggiornato. Totale lordo: {sum(r['totale'] for r in inv_zero_residuo):,.2f} €
2. Alcuni BSL orfani potrebbero coprire fatture **già pagate** (riconciliate altrove) che non appaiono in questo audit
3. Pagamenti multipli su stessa fattura con riconciliazione parziale

---

## Match proposti

**{len(all_matches)} match trovati** per un totale di **{matched_amount:,.2f} €**

"""
    if all_matches:
        report += "| BSL ID | Data BSL | Importo BSL | Fattura | Ref | Residuo FT | Tipo match |\n"
        report += "|--------|----------|-------------|---------|-----|------------|------------|\n"
        for m in sorted(all_matches, key=lambda x: x['bsl_data']):
            report += f"| {m['bsl_id']} | {m['bsl_data']} | {m['bsl_importo']:,.2f} € | {m['fattura_numero']} | {m['fattura_ref']} | {m['fattura_residuo']:,.2f} € | {m['tipo_match']} |\n"

    report += f"""
---

## Pagamenti senza match ({len(unmatched_payments)})

Totale: **{unmatched_payment_amount:,.2f} €**

"""
    if unmatched_payments:
        report += "| BSL ID | Data | Importo | Tipo | Descrizione |\n"
        report += "|--------|------|---------|------|-------------|\n"
        for p in sorted(unmatched_payments, key=lambda x: x['data']):
            report += f"| {p['id']} | {p['data']} | {p['importo']:,.2f} € | {p['tipo']} | {p['descrizione']} |\n"

    report += f"""
---

## Fatture/NC con residuo aperto senza match ({len(unmatched_inv)})

"""
    unmatched_ft = [r for r in unmatched_inv if r['tipo'] == 'in_invoice']
    unmatched_nc = [r for r in unmatched_inv if r['tipo'] == 'in_refund']

    if unmatched_ft:
        report += f"### Fatture ({len(unmatched_ft)}, residuo totale: {unmatched_inv_residuo:,.2f} €)\n\n"
        report += "| ID | Numero | Data | Ref | Totale | Residuo |\n"
        report += "|----|--------|------|-----|--------|---------|\n"
        for r in sorted(unmatched_ft, key=lambda x: x['data']):
            report += f"| {r['id']} | {r['numero']} | {r['data']} | {r['riferimento']} | {r['totale']:,.2f} € | {r['residuo']:,.2f} € |\n"

    if unmatched_nc:
        report += f"\n### Note Credito ({len(unmatched_nc)}, residuo totale: {unmatched_nc_residuo:,.2f} €)\n\n"
        report += "| ID | Numero | Data | Ref | Totale | Residuo |\n"
        report += "|----|--------|------|-----|--------|---------|\n"
        for r in sorted(unmatched_nc, key=lambda x: x['data']):
            report += f"| {r['id']} | {r['numero']} | {r['data']} | {r['riferimento']} | {r['totale']:,.2f} € | {r['residuo']:,.2f} € |\n"

    report += f"""
---

## Totali di dettaglio

### Fatture aperte
- **{inv_count}** fatture, totale lordo **{inv_total:,.2f} €**, residuo **{inv_residuo:,.2f} €**
- **{nc_count}** note credito, totale lordo **{nc_total:,.2f} €**, residuo **{nc_residuo:,.2f} €**
- Residuo netto: **{residuo_netto:,.2f} €**

### Anomalia: fatture residuo=0 ma not_paid
**{len(inv_zero_residuo)} fatture** risultano con `amount_residual = 0` ma `payment_state = 'not_paid'`.
Queste fatture sono state chiuse contabilmente (le righe AML sono riconciliate) ma lo stato pagamento non si è aggiornato.
Totale lordo coinvolto: **{sum(r['totale'] for r in inv_zero_residuo):,.2f} €**

<details><summary>Lista completa</summary>

| Numero | Data | Ref | Totale |
|--------|------|-----|--------|
"""
    for r in sorted(inv_zero_residuo, key=lambda x: x['data']):
        report += f"| {r['numero']} | {r['data']} | {r['riferimento']} | {r['totale']:,.2f} € |\n"

    report += f"""</details>

### BSL bancari con partner Arpaia (partner_id=4956)
- **{len(d3)} righe** totali, **{len(d3_outflows)} outflow** per **{d3_total_outflow:,.2f} €**
- Tutti su **Revolut** (journal_id=13)
- **Zero BSL su Qonto (id=6) o BCC (id=22)**

### BSL orfani (partner_id=NULL, testo ARPAIA)
- **{len(d4)} pagamenti** in uscita per **{d4_total:,.2f} €**
- Tutti su **Revolut** (journal_id=13)
- Nessun BSL orfano su Qonto o BCC

### Riepilogo pagamenti per canale
| Canale | Righe outflow | Importo |
|--------|---------------|---------|
| Revolut (partner-tagged) | {len(d3_outflows)} | {d3_total_outflow:,.2f} € |
| Revolut (orfani) | {len(d4)} | {d4_total:,.2f} € |
| Qonto | 0 | 0,00 € |
| BCC | 0 | 0,00 € |
| **Totale** | **{len(d3_outflows) + len(d4)}** | **{total_payments:,.2f} €** |

---

## Prossimi passi

1. **Assegnare partner ai BSL orfani**: i {len(d4)} BSL Revolut orfani hanno `partner_id=NULL`. Settare `partner_id=4956` per abilitare la riconciliazione nel widget Odoo.

2. **Riconciliare i {len(all_matches)} match proposti**: usare il widget di riconciliazione Odoo per collegare ciascun BSL alla fattura corrispondente.

3. **Investigare i {len(unmatched_payments)} pagamenti senza match**: verificare se coprono fatture già pagate o se sono pagamenti duplicati.

4. **Verificare le {len(inv_zero_residuo)} fatture residuo=0/not_paid**: probabilmente serve un `_compute_amount()` o richiamo del cron di ricalcolo. Se confermato, sono "false aperte" e il debito reale è inferiore.

5. **Investigare pagamenti composti D3**: le 2 entry compound (2025-08-06: 5.501,08 € e 2025-12-09: 843,46 €) contengono "Open balance" — verificare se sono pagamenti cumulativi di più fatture e smontarli.

6. **NC non matchate**: le {len(unmatched_nc)} NC con residuo ({unmatched_nc_residuo:,.2f} €) devono essere compensate con le fatture corrispondenti.

---

*Audit generato automaticamente il 2026-05-15. Solo operazioni SELECT eseguite sul DB folinofood.*
"""

    with open(os.path.join(OUT, 'report.md'), 'w', encoding='utf-8') as f:
        f.write(report)
    print("  -> report.md generato")


if __name__ == '__main__':
    main()
