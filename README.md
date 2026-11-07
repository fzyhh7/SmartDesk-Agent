# SmartDesk-Agent 路 浼佷笟鍐呴儴鏈嶅姟鍙?Agent

**鐢ㄨ嚜鐒惰瑷€闂埗搴︺€佹煡宸ュ崟銆佸缓鍗曘€佸叧鍗曘€侫gent 瑕佷箞缁欏嚭甯﹀紩鐢ㄧ殑绛旀锛岃涔堟妸鍐欐搷浣滃仛鎴愬垎绾ч椄闂ㄢ€斺€斿彧璇荤洿閫氾紝鍙€嗗啓瑕佹湰浜虹‘璁わ紝涓嶅彲閫?瀵瑰瑕佷富绠″鎵癸紝鍋滀笅鏃剁姸鎬佸啓杩?checkpoint锛屾崲涓繘绋嬩篃鑳芥帴鐫€鎵广€?*

![浼氳瘽宸ヤ綔鍙帮細涓€娆″叧鍗曞姩浣滃仠鍦ㄥ鎵归椄闂╙(docs/screenshots/02-chat-approval.png)

鏍稿績涓嶆槸"鎶婄煡璇嗗簱鎺ヨ繘妯″瀷"锛岃€屾槸鎶?**鍥炵瓟** 鍜?**鍔ㄤ綔** 鍒嗗紑锛?
- **鍥炵瓟**鍙緷鎹绱㈠埌鐨勫埗搴︼紝寮哄埗甯?`[1][2]` 寮曠敤锛屾壘涓嶅埌灏辫"鐭ヨ瘑搴撴病鏈夎繖鏉?骞剁粰涓嬩竴姝ワ紱
- **鍔ㄤ綔**鎸夊嵄闄╃▼搴﹀垎绾э紝椋庨櫓涓嶆槸闈欐€侀厤缃細鍏冲崟鏃跺嬀浜?閫氱煡鎻愬崟浜?锛岄闄╁氨浠庛€屽彲閫嗗啓銆嶈嚜鍔ㄥ崌鍒般€屼笉鍙€嗗啓銆嶏紱
- **璋佹壒鍑?*鐢辨潈闄愮畻鍑烘潵锛屼笉鐢卞璇濋噷璇翠簡浠€涔堢畻锛氭仮澶嶆椂鎸夋仮澶嶄汉鐨勮鑹蹭簩娆￠壌鏉冿紝鍙戣捣浜烘壒鑷繁鐨勫崟浼氳鏍?`self_approved`銆?
## 30 绉掔湅鎳?
| | |
|---|---|
| **9 鑺傜偣 / 5 鏉¤矾鐢?* | 鍒嗘敮鍏ㄩ儴闆嗕腑鍦?`backend/app/agents/graph.py`锛岃妭鐐瑰彧杩斿洖瀛楁锛岃矾鐢辨墠鐭ラ亾涓嬩竴绔?|
| **3 绾ч闄╅椄闂?* | `action_spec.py` 鐨?`RISK_BY_OP` + `compute_risk()`锛氬悓涓€鍔ㄤ綔甯︿笉鍚屽弬鏁帮紝椋庨櫓鍙互涓嶅悓 |
| **璺ㄨ繘绋嬪鎵?* | `interrupt` 鎸傝捣 鈫?璁板綍杩?`approvals`锛堝甫 `thread_id`锛夆啋 瀹℃壒涓績鐐逛竴涓嬶紝鐢ㄥ悓涓€涓?`thread_id` resume |
| **2 涓?MCP server / 9 涓伐鍏?* | 宸ュ崟搴撳拰鐭ヨ瘑搴撳悇涓€涓?FastMCP server锛?*閴存潈鍦?server 渚?*锛堝悓绉熸埛 + 鏈汉/鐗规潈锛夛紝涓嶉潬鍓嶇钘忔寜閽?|
| **浜岀骇娣峰悎妫€绱?* | Milvus 绋犲瘑 1024 缁?+ 鍐呯疆涓枃 BM25 缁?`RRFRanker(k=60)` 绮楁帓 Top-10 鈫?`gte-rerank-v2` Cross-Encoder 绮炬帓铻嶅悎鍙?Top-3锛堝甫 `tenant_id` 杩囨护涓庡紓甯歌嚜鍔ㄩ檷绾э級 |
| **鏈夎瘎娴嬩笌娑堣瀺** | 51 鏉℃爣娉ㄩ棶鍙ワ細Recall@1 **86.27%**锛?3.92pp锛夈€丷ecall@3 **98.04%**锛?1.96pp锛夈€丮RR@3 **0.9150**锛?0 鏉＄鍒扮鐢ㄤ緥寮曠敤鍑嗙‘鐜?**100%** |

## 鏋舵瀯

```mermaid
flowchart TD
  S([鐢ㄦ埛鎻愰棶]) --> C["classify_request<br/>鎰忓浘鍒嗙被锛歝hat / knowledge / action"]

  C -->|chat| R["compose_reply<br/>闂茶亰鐩存帴鍥烇紝涓嶆绱?]
  C -->|knowledge / action| G["gather_evidence<br/>妫€绱㈠埗搴?+ 鏌ュ伐鍗曚簨瀹?]

  G -->|knowledge| A["answer_with_citations<br/>鍙緷鎹绱㈢粨鏋滐紝寮哄埗寮曠敤"]
  G -->|action| P["plan_action<br/>鍙傛暟鎶藉彇 + 鏉冮檺棰勬 + 瀹氶闄?]

  P -->|缂哄繀濉弬鏁皘 M["ask_missing_info<br/>clarify 闂搁棬"]
  M --> P

  P -->|鍙 read| E["execute_action<br/>鍏ㄥ浘鍞竴鍐欒妭鐐?]
  P -->|鍙€嗗啓 write_reversible| CF["confirm_action<br/>鏈汉纭"]
  P -->|涓嶅彲閫嗗啓 write_irreversible| AP["approve_action<br/>涓荤瀹℃壒"]

  CF -->|鏀瑰弬鏁板鑷撮闄╁崌绾 AP
  CF --> E
  AP --> E

  A --> R
  E --> R
  R --> END([杩斿洖鍓嶇 / CLI])
```

涓ゆ潯鍏抽敭绾︽潫鍐欐鍦ㄤ唬鐮侀噷锛屼笉闈犳彁绀鸿瘝锛?
1. **鍙湁 `execute_action` 浼氬啓**锛屼笖鎵ц鍓嶅啀鍏滃簳涓€娆?`state["risk"] == "write_irreversible" and not approved`锛?2. **闂搁棬鏄?`interrupt` 涓嶆槸寮圭獥**锛氱姸鎬佸瓨 checkpoint锛岃繘绋嬮噸鍚悗鍚屼竴 `thread_id` 浠嶅彲 resume 鈥斺€?杩欐槸"璺ㄨ繘绋嬩汉宸ュ鎵?鐨勫疄鐜版柟寮忋€?
## 鐣岄潰

| 浼氳瘽宸ヤ綔鍙?| 瀹℃壒涓績 |
|---|---|
| ![娆㈣繋椤礭(docs/screenshots/01-welcome.png) | ![瀹℃壒鐪嬫澘](docs/screenshots/03-approvals.png) |

鍙充晶銆岃繍琛屾椂銆嶉潰鏉挎妸 Agent 鐨?9 涓妭鐐广€侀闄╅樁姊€佺粨鏋勫寲缁撴灉鍜岀瓑浠峰懡浠よ閮芥憡寮€鈥斺€旀紨绀烘椂鍙互鐩存帴鎸囩潃璇?瀹冨仠鍦ㄨ繖涓€鏍硷紝鏄洜涓洪€氱煡鍙戝嚭鍘绘挙涓嶅洖"銆?
| 瀹℃壒鍗曟嵁锛堝彲瀹￠槄锛?| 宸ュ崟鐪嬫澘 |
|---|---|
| ![瀹℃壒鍗曟嵁](docs/screenshots/02-chat-approval.png) | ![宸ュ崟鐪嬫澘](docs/screenshots/04-tickets.png) |

闂搁棬鍗＄墖琚仛鎴愪竴寮?*鍙闃呯殑鍗曟嵁**锛氫负浠€涔堣瀹℃壒銆佹瘡涓弬鏁颁粠鍝潵锛堜綘璇寸殑璇?/ 璇佹嵁鍥炲～ / 涓婁笅鏂囷級銆佸鎵归摼涓婅皝鏄彂璧蜂汉璋佹槸寰呮壒浜猴紝閮藉湪鍗＄墖閲屻€?
鍒楄〃椤电殑鍐呭鍖烘湁浜旂鐘舵€侊細璇诲彇涓紙楠ㄦ灦锛?/ 鐪熺殑娌℃湁鏁版嵁 / 绛涢€夊悗涓虹┖ / 璇诲け璐?/ **鍚庣娌¤繛涓?*锛堢洿鎺ユ妸鍚姩鍛戒护鍐欏湪椤甸潰涓棿锛岄伩鍏?鐪嬭捣鏉ュ儚绌虹殑"锛夈€傛渶鍚庝竴绉嶇殑鏍峰瓙瑙?[06-backend-down.png](docs/screenshots/06-backend-down.png)銆?
## 鎶€鏈爤

| 灞?| 鎶€鏈?|
|---|---|
| 缂栨帓 | LangGraph 1.x锛坄StateGraph` / `interrupt` / `Command` / checkpointer锛?|
| 妯″瀷 | LangChain 1.x锛坄init_chat_model`锛涘垎绫昏蛋缁撴瀯鍖栬緭鍑猴紝鍙傛暟鎶藉彇璧扮‘瀹氭€ц鍒欙級 |
| 妫€绱?| Milvus锛堢瀵?1024 缁?+ 鍐呯疆 BM25锛屾湇鍔＄ `RRFRanker(k=60)` 绮楁帓锛? DashScope `gte-rerank-v2` Cross-Encoder 绮炬帓 |
| 宸ュ叿 | FastMCP 2 涓?server锛? 涓伐鍏凤級锛宍MultiServerMCPClient` 瑁呴厤锛屾潈闄愬湪 server 渚?|
| 鎸佷箙鍖?| PostgreSQL锛坄PostgresSaver`锛? 鏈湴 SQLite 鍏滃簳锛沗approvals` 琛ㄥ瓨瀹℃壒 |
| 鍚庣 | FastAPI + SSE锛坄/chat/stream`銆乣/runs/{id}/resume` 绛夛級 |
| 鍓嶇 | Vue3 + Vite + TypeScript + Element Plus锛堟繁搴﹀畾鍒讹紝浼氳瘽 / 瀹℃壒 / 宸ュ崟涓夐〉锛?|

## 鐩綍

```
backend/app/
  agents/           涓诲浘涓庤妭鐐癸細graph.py state.py checkpoint.py knowledge.py
    nodes/          9 涓妭鐐?+ 鍔ㄤ綔瑙勫垯琛紙action_spec.py锛?    rag/            Milvus 璇诲啓銆丆ross-Encoder 绮炬帓锛坮eranker.py锛夈€乪mbedding銆丮inerU 瑙ｆ瀽銆佺粨鏋勬劅鐭ュ垏鍒?    tools/          MCP 瀹㈡埛绔笌宸ュ叿灏佽
    prompts/        鍒嗙被 / 浣滅瓟 / 闂茶亰鎻愮ず璇?  mcp/servers/      ticket_server.py / kb_server.py / guard.py锛堥壌鏉冿級
  api/              main.py routes.py streaming.py deps.py
frontend/src/        styles/锛堣璁?token锛塩omponents/ views/ stores/ utils/
scripts/             run_graph锛圕LI锛? ingest_docs锛堝叆搴擄級/ eval_rag锛堣瘎娴嬶級/ trace_run / reset_demo锛堥噸缃紨绀烘暟鎹級
deploy/              docker-compose.yml锛圡ilvus / etcd / PostgreSQL / attu锛?docs/kb/             鐭ヨ瘑搴撴簮鏂囨。锛? 浠借櫄鏋勫埗搴︼級銆丳DF銆佽В鏋愪骇鐗┿€乧hunks
docs/eval/           51 鏉¤瘎娴嬮泦涓庢姤鍛?docs/screenshots/    鐣岄潰鎴浘
```

## 蹇€熷紑濮?
```bash
# 0) 鐜锛歅ython 3.12 + Node 20+ + Docker Desktop
uv sync                                        # 鎴栵細python -m venv .venv && .venv/Scripts/pip install -e .

# 1) 渚濊禆鏈嶅姟锛圡ilvus / PostgreSQL锛宒eploy/.env 宸查厤濂介粯璁ょ鍙ｄ笌闀滃儚锛?docker compose -f deploy/docker-compose.yml up -d
docker compose -f deploy/docker-compose.yml ps      # 绛?milvus healthy

# 2) 閰嶇疆鐜鍙橀噺锛堣嚜宸卞～ key锛屼笉瑕佹彁浜わ級
cp .env.example .env    # 濉?DEEPSEEK_API_KEY銆丏ASHSCOPE_API_KEY

# 3) CLI锛氱煡璇嗛棶绛?/ 寤哄崟 / 瀹℃壒
.venv/Scripts/python.exe -m scripts.run_graph run --thread t1 -m "骞村亣鏈夊灏戝ぉ锛?
.venv/Scripts/python.exe -m scripts.run_graph run --thread t2 -m "甯垜寤轰釜宸ュ崟锛歏PN 杩炰笉涓?
.venv/Scripts/python.exe -m scripts.run_graph resume --thread t2 --approve

# 4) HTTP + SSE
.venv/Scripts/python.exe -m uvicorn backend.app.api.main:app --port 8010

# 5) 鍓嶇锛堝彟寮€缁堢锛?cd frontend && npm install && npm run dev     # 娴忚鍣ㄥ紑 http://localhost:5173
```

棣栨浣跨敤闇€瑕佸叆搴擄紙浠撳簱鏈彁浜ゅ悜閲忔暟鎹級锛?
```bash
.venv/Scripts/python.exe -m scripts.ingest_docs --md docs/kb/md --to-milvus
```

## 涓€鍒嗛挓婕旂ず鑴氭湰

1. **鐭ヨ瘑闂瓟**锛歚骞村亣鏈夊灏戝ぉ锛焋 鈫?绛斿甯?`[1][2]` 寮曠敤锛屽彸渚ц兘鐪嬪埌 `gather_evidence` 鐨勮€楁椂锛?2. **鍙€嗗啓**锛歚甯垜寤轰釜宸ュ崟锛氫細璁鎶曞奖浠病淇″彿` 鈫?鍋滃湪**纭**闂搁棬锛屾敼涓€涓嬫爣棰樺啀鐐归€氳繃锛屽伐鍗曡惤搴擄紱
3. **涓嶅彲閫嗗啓**锛歚鎶?TK-20261106-0005 鍏虫帀骞堕€氱煡鎻愬崟浜篳 鈫?椋庨櫓浠庛€屽彲閫嗗啓銆嶅崌绾т负銆屼笉鍙€嗗啓銆嶏紝鍋滃湪**瀹℃壒**闂搁棬锛?4. **鎹汉瀹℃壒**锛氬乏涓嬭韬唤鍗″垏鎴愪富绠★紙`u-9001`锛夆啋 瀹℃壒涓績鐐广€岄€氳繃銆嶁啋 浼氳瘽鐢ㄥ師 `thread_id` 鎭㈠鎵ц锛屽伐鍗曠姸鎬佸彉 `closed`锛?5. **瓒婃潈婕旂ず**锛氬垏鎴愬憳宸?`u-7777` 鏌ュ埆浜虹殑鍗?鈫?`outcome=denied`锛屾彁绀?鍙湁鎻愬崟浜烘湰浜烘垨涓荤鑳藉鐞?銆?
## 璇勬祴

51 鏉℃爣娉ㄩ棶鍙ワ紙鏍囨敞鍒?鏂囨。 + 灏忚妭"锛夊 97 涓?chunk锛屾敮鎸佷竴閿窇绾?RRF 绮楁帓 vs RRF+Cross-Encoder 绮炬帓娑堣瀺瀵圭収鍙?20 鏉＄鍒扮寮曠敤鍑嗙‘鐜囷細

```bash
.venv/Scripts/python.exe -m scripts.eval_rag --compare --answers 20
```

| 鏂规 / 鎸囨爣 | Recall@1 | Recall@3 | MRR@3 | 妫€绱㈠钩鍧?/ P95 寤惰繜 |
|---|---|---|---|---|
| Dense + BM25 + RRF (Top-3) | 82.35% | 96.08% | 0.8922 | 235 / 330 ms |
| **+ `gte-rerank-v2` 绮炬帓 (Top-10 鈫?Top-3)** | **86.27%** (+3.92pp) | **98.04%** (+1.96pp) | **0.9150** (+0.0228) | 382 / 486 ms |

- **绔埌绔洖绛旓紙20 鏉＄湡妯″瀷锛?*锛氬紩鐢ㄥ噯纭巼 **100%**銆佸紩鐢ㄦ爣璁扮巼 **100%**锛屽钩鍧囪€楁椂 3.37 s / P95 4.22 s锛堣瑙?[`docs/eval/report.md`](docs/eval/report.md)锛夈€?
## 婕旂ず鏁版嵁璇存槑

`docs/kb/src/` 鏄?*铏氭瀯鍏徃銆屾槦婢滅鎶€銆嶇殑鍒跺害鏂囨。**锛堟枃涓凡鏍囨敞"鎶€鏈紨绀虹敤鐨勮櫄鏋勭ず渚?锛夛紝鐢辫剼鏈敓鎴?PDF 鍚庣粡 MinerU 瑙ｆ瀽鍏ュ簱銆傚伐鍗曞簱閲岀殑鏁版嵁閮芥槸婕旂ず鏁版嵁銆?
## 閲嶇疆婕旂ず鏁版嵁

婕旂ず璺戝畬鎯冲洖鍒板共鍑€鐘舵€侊紝鐢?`scripts/reset_demo.py`銆?*榛樿 dry-run**锛屽彧鎵撳嵃"浼氬垹浠€涔?锛屽姞 `--yes` 鎵嶇湡鐨勫垹锛?
```bash
# 鐪嬩竴鐪间細鍒犱粈涔堬紙涓嶆墽琛岋級
.venv/Scripts/python.exe -m scripts.reset_demo

# 娓呯┖宸ュ崟 + 瀹℃壒 + 鍏ㄩ儴浼氳瘽锛屼繚鐣欑煡璇嗗簱
.venv/Scripts/python.exe -m scripts.reset_demo --yes --keep-kb

# 鍙竻鎺夌綉椤电璺戝嚭鏉ョ殑浼氳瘽锛屼繚鐣欏伐鍗?.venv/Scripts/python.exe -m scripts.reset_demo --yes --threads "web-*" --keep-tickets

# 杩炵煡璇嗗簱涔熼噸寤猴紙涓嬫 ingest 鍓嶆槸绌虹殑锛?.venv/Scripts/python.exe -m scripts.reset_demo --yes --kb
```

瀹冨垹鐨勫彧鏈変袱绫讳笢瑗匡細SQLite 閲岀殑 `tickets` / `approvals` 琛岋紙琛ㄧ粨鏋勪繚鐣欙級锛屼互鍙?checkpoint 閲岀殑浼氳瘽绾跨▼銆傜煡璇嗗簱 chunk 榛樿淇濈暀锛屽洜涓洪噸寤鸿璺戜竴娆?MinerU + 宓屽叆锛屾瘮杈冩參銆?
鎯虫嬁鍓湰搴撴紨缁冭€屼笉纰扮湡鏁版嵁锛岀敤 `TICKET_DB_PATH` 鎸囪繃鍘诲氨琛岋紙鍚庣涓?CLI 閮戒細璁よ繖涓彉閲忥紝MCP 瀛愯繘绋嬩篃浼氬師鏍烽€忎紶锛夛細

```bash
cp .data/tickets.sqlite .tmp-copy.sqlite
TICKET_DB_PATH=.tmp-copy.sqlite .venv/Scripts/python.exe -m scripts.reset_demo --yes --keep-threads
```

## 宸茬煡杈圭晫

- 娌℃湁鐧诲綍/JWT锛氳韩浠借蛋璇锋眰澶达紙`X-User-Id` / `X-Tenant-Id` / `X-Roles`锛夛紝鏉冮檺鍦?MCP server 渚ф牎楠岋紱
- 鏈仛妫€绱㈠墠 Query Rewrite锛氭渶鍚?1 鏉℃湭杩?Top-3 鐨勯棶鍙ワ紙`g49`锛?鎴戣兘鏌ュ埌鍒殑瀛愬叕鍙哥殑宸ュ崟鍚? vs 鍒跺害鏈"璺ㄧ鎴疯闂?锛夊湪鍙岃矾鍒濈瓫 Top-20 闃舵鍗宠楂橀璇?宸ュ崟"鎸ゅ嚭鍊欓€夋睜锛岄渶缁撳悎鍚屼箟璇嶆敼鍐欐垨鏇村ぇ鍊欓€夋睜杩涗竴姝ュ彫鍥烇紱
- 鍗?Agent锛氬崟閾捐矾涓氬姟锛屾媶澶?Agent 鍙細澶氬悓姝ユ垚鏈紱
- 瀹℃壒鍙仛"鍏冲崟骞堕€氱煡""鍙戝竷鐭ヨ瘑"涓ょ被涓嶅彲閫嗗姩浣滐紝鏈鐩栨淳鍗?/ SLA / 娴佽浆锛?- 鍙傛暟鎶藉彇鏄鍒欎笉鏄ā鍨嬶細鐪佷竴娆?LLM 璋冪敤銆侀槻鍗曞彿骞昏锛屾娊涓嶅埌鐨勪氦缁?`ask_missing_info` 鍙嶉棶锛?- 瀹℃壒瀹屾垚鍚?*鍙戣捣浜轰笉浼氭敹鍒版帹閫?*锛氬鎵逛腑蹇冩敼鐨勬槸 `approvals` 琛ㄥ拰浼氳瘽鐨?checkpoint锛屽憳宸ラ偅椤佃鍐嶅彂涓€鍙ヨ瘽 / 鍒锋柊鎵嶇湅寰楀埌缁撴灉锛堢湡瀹炵郴缁熻繖閲岃鎺ユ秷鎭€氱煡锛夛紱
- 涓€鏉?thread 鍚屾椂鍙兘鏈変竴涓寕璧蜂腑鐨勫緟鍔烇細鎸傝捣鏈熼棿鍐嶅彂娑堟伅浼氳繑鍥?409锛岄伩鍏嶆妸 checkpoint 鍐叉帀锛堝墠绔凡鎻愮ず鍏堝鐞嗗崱鐗囷級銆?
## 杩愯鏃舵敞鎰?
- **kb server 鍚姩浼氶鐑?import**锛坄backend/app/mcp/servers/kb_server.py` 鐨?`_warmup()`锛夛細FastMCP 鎶婂悓姝ュ伐鍏锋斁鍒?worker 绾跨▼鎵ц锛宍pymilvus`/`numpy` 鐨?C 鎵╁睍鍦ㄨ绾跨▼閲岄娆?import 浼氬崱浣忎笉杩斿洖锛涙彁鍓嶅湪涓荤嚎绋?import 涓€娆★紝浠ｄ环鏄瘡涓?kb 宸ュ叿瀛愯繘绋嬪绾?1 绉掑惎鍔ㄦ椂闂淬€?- 鐭ヨ瘑鏂囩珷鐨勫彲瑙佹€у彧鏈?`published` 涓€绉嶇姸鎬侊紙瀹℃壒鍦ㄥ啓涔嬪墠锛夛紝`doc_status` 宸茬粡鏄?`vector_store.DOC_STATUS_PUBLISHED` 杩欎釜甯搁噺锛岃鍐欓兘涓嶅啀浼犲弬銆?
