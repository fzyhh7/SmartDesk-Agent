# AI Agent 浼佷笟绾ч」鐩細鐭ヨ瘑澶х翰 + 椤圭洰鏂瑰悜閫夋嫨

> **璧勬枡鍩虹**锛氶粦椹▼搴忓憳 AI Agent 璇剧▼ 11 浠借涔夛紙LangChain 鏍稿績缁勪欢銆丄I绉佸帹瀹炴垬銆丷untime銆丮iddleware銆丮CP銆丮ulti Agent銆丷AG Agent銆丮ilvus銆丩angGraph 鍩烘湰姒傚康銆佸父瑙?WorkFlow銆乀hink In LangGraph锛? 浣犲凡鏈夌殑 FastAPI / Vue 鑳藉姏銆?> **鎬庝箞璇昏繖浠芥枃妗?*锛氱 0 绔犵湅缁撹 鈫?绗?1 绔犲鐓ф墦閽╋紙鐭ラ亾鑷繁浼氫粈涔堬級鈫?绗?2 绔犵煡閬撶畝鍘嗛噷蹇呴』鍐欎粈涔?鈫?绗?3 绔犻€夋柟鍚?鈫?绗?4/5 绔犵洿鎺ュ紑宸ャ€?> **璇剧▼鐗堟湰鎻愰啋**锛氳繖濂楄涔夋槸 **LangChain 1.x + LangGraph 1.x** 鐨勫啓娉曪紙`create_agent`銆丮iddleware銆丷untime銆乣Command`銆乣interrupt`锛夛紝涓庣綉涓婂ぇ閲?0.x 鏁欑▼锛圓gentExecutor銆乣initialize_agent`锛変笉鍏煎銆傞潰璇曡闂埌鏃讹紝鑳借娓?鎴戠敤鐨勬槸 v1 鐨?create_agent + middleware 鏋舵瀯"鏈韩灏辨槸鍔犲垎椤广€?
---

> **鐗堟湰璇存槑锛堟渶鏂板悓姝ワ細浠ｇ爜閲嶆瀯涔嬪悗锛?*
> 绗?1銆? 绔犳槸**榛戦┈璇剧▼鐭ヨ瘑鐐规€荤粨**锛屼笌椤圭洰瀹炵幇鏃犲叧锛屼繚鎸佸師鏍蜂笉鍔ㄣ€?> 绗?3 绔犺捣鍙**杩欎竴涓畾绋块」鐩?*锛圫martDesk AI 浼佷笟鍐呴儴鏈嶅姟鍙帮級锛屾棭鏈熺殑 B/C/D/E 澶囬€夋柟鍚戝凡鍒犻櫎銆?> 椤圭洰鐜扮姸锛氫節鑺傜偣 + 涓夐椄闂?+ 9 涓?MCP 宸ュ叿 / 2 涓?server锛堝伐鍗?5 + 鐭ヨ瘑 2 + 娌荤悊 2锛夈€丮ilvus 鏈嶅姟绔贩鍚堟绱€丳ostgresSaver 鎸佷箙鍖栥€佸鎵硅惤琛ㄣ€佸彧鐢ㄧ湡妯″瀷锛堟棤绂荤嚎鍏滃簳锛夈€佹棤娴嬭瘯鐩綍銆傜 4 绔犱笌浠撳簱浠ｇ爜涓€涓€瀵瑰簲銆?
## 0. 缁撹閫熻

1. **璇剧▼宸茬粡鎶婁紒涓氱骇 Agent 鐨勯鏋惰瀹屼簡**锛歚create_agent` 鐨?7 涓敞鍏ョ偣锛坢odel / tools / system_prompt / state_schema / context_schema / checkpointer / store / middleware锛夈€丩angGraph 缂栨帓銆丷AG + Milvus 娣峰悎妫€绱€丮CP 宸ュ叿鎺ュ叆銆丮ulti-Agent 鍗忎綔銆備綘缂虹殑涓嶆槸鐭ヨ瘑鐐癸紝鑰屾槸**鎶婂畠浠覆鎴愪竴鏉℃湁涓氬姟闂幆銆佹湁璇勬祴鏁版嵁銆佽兘閮ㄧ讲涓婄嚎鐨勪富绾?*銆?2. **绠€鍘嗛」鐩殑鍒嗘按宀笉鏄?鐢ㄤ簡澶氬皯妗嗘灦"锛岃€屾槸鍥涗欢浜?*锛氱湡瀹炰笟鍔℃祦绋嬨€佷汉宸ヤ粙鍏ワ紙HITL锛夈€佹绱?璐ㄩ噺鏁版嵁銆侀儴缃蹭笌鍙娴嬨€傚彧鍋?鑱婂ぉ + 鐭ヨ瘑搴?鐨勯」鐩湪 2026 骞寸殑瀹炰範绠€鍘嗛噷宸茬粡娉涙互锛屽繀椤绘湁浼佷笟鍖栫壒寰侊紙澶氱鎴枫€佸鎵广€佸璁°€侀檷绾с€佹垚鏈級銆?3. **椤圭洰宸插畾绋?*锛氫紒涓氭櫤鑳藉伐鍗曚笌鐭ヨ瘑搴?Agent 骞冲彴锛圫martDesk AI锛夈€備唬鐮佸凡瀹屾垚 1鈥? 闃舵锛堜節鑺傜偣 + 涓夐椄闂?+ 9 宸ュ叿 + 瀹℃壒钀借〃 + Milvus 娣峰悎妫€绱?+ PostgresSaver + FastAPI/SSE锛夛紝鍓╀笅 Vue3 涓夐〉涓庡彲瑙嗗寲鍖呰銆?
---

## 1. 璇剧▼鐭ヨ瘑鐐瑰叏閲忔竻鍗曪紙鎸?椤圭洰涓殑鐢ㄩ€?閲嶆帓锛?
> 鍥句緥锛?*鈽?涓婚」鐩繀椤昏惤鍒颁唬鐮?* 锝?**鈽?鍔犲垎锛堝啓杩涚畝鍘?闈㈣瘯鑳借锛?* 锝?鏃犳爣璁?= 浜嗚В鍗冲彲銆?> "璁蹭箟"鍒楀搴斾綘缁欑殑 11 浠芥枃妗ｏ紝鏂逛究鍥炲ご鏌ュ師璇俱€?
### 1.1 LangChain 鍐呮牳锛堣涔夛細LangChain路绗?鑺?鏍稿績缁勪欢锛?
| 鐭ヨ瘑鐐?| 璁蹭箟涓殑绮剧‘ API / 鍐欐硶 | 椤圭洰涓殑钀界偣 | 绾у埆 |
|---|---|---|---|
| 妯″瀷鍒濆鍖栦笌澶氭ā鍨嬪垏鎹?| `init_chat_model(model=..., model_provider="openai", base_url=..., api_key=...)`锛沗ChatTongyi(model="qwen-plus")`锛沗temperature/max_tokens/max_retries` | 缁熶竴妯″瀷璺敱锛歞eepseek / qwen / OpenAI 鍙垏鎹?| 鈽?|
| Agent 鍒涘缓锛坴1 鏍稿績锛?| `create_agent(model, tools, system_prompt, state_schema, context_schema, checkpointer, store, middleware, response_format)` | 鎵€鏈変笟鍔?Agent 鐨勭粺涓€鍏ュ彛 | 鈽?|
| 娑堟伅浣撶郴 | `SystemMessage/HumanMessage/AIMessage/ToolMessage`锛沗response["messages"]`锛沗content_blocks` | SSE 娴佸紡娓叉煋銆佸伐鍏疯皟鐢ㄥ洖鏄?| 鈽?|
| 澶氭ā鎬佹秷鎭?| `content=[{"type":"image","url":...},{"type":"text","text":...}]`锛涙湰鍦板浘璧?base64 + `mime_type` | 宸ュ崟鎴浘/鍥剧墖闄勪欢璇嗗埆锛圲RL 璧板璞″瓨鍌紝鍒 base64锛?| 鈽?|
| 宸ュ叿瀹氫箟 | `@tool`锛沗@tool("name", description=...)`锛沗@tool(args_schema=PydanticModel)`锛涗繚鐣欏弬鏁?`config`銆乣runtime` 涓嶅彲鍗犵敤锛沗tool.invoke({...})` | 妫€绱€佸缓鍗曘€佹煡璁㈠崟銆佸彂閭欢 | 鈽?|
| 缁撴瀯鍖栬緭鍑?| `response_format=PydanticModel` 鈫?`response["structured_response"]`锛沗llm.with_structured_output(...)` | 鎰忓浘鍒嗙被銆佸伐鍗曞瓧娈垫娊鍙栥€佽瘎浼板櫒鎵撳垎 | 鈽?|
| 娴佸紡 | `stream_mode="messages"` / `"updates"`锛沗stream_events(version="v3")` | 鍓嶇閫愬瓧杈撳嚭 + 鎬濊€冭繃绋?+ 宸ュ叿杩涘害 | 鈽?|
| 鐭湡璁板繂 | `checkpointer=InMemorySaver()` / `SqliteSaver(sqlite3.connect(..., check_same_thread=False))` + `checkpointer.setup()`锛沗config={"configurable":{"thread_id":...}}` | 浼氳瘽鎸佷箙鍖栥€佹柇鐐规仮澶?| 鈽?|
| 璁板繂绠＄悊 | `SummarizationMiddleware(model=..., trigger=("messages",3), keep=("messages",1))`锛涗慨鍓?/ 鍒犻櫎娑堟伅 | 闀夸細璇濅笂涓嬫枃涓庢垚鏈帶鍒?| 鈽?|
| LangSmith | `LANGSMITH_TRACING=true`銆乣LANGSMITH_PROJECT`锛汼tudio 璋冭瘯 | 鍙娴嬨€佽瘎娴嬨€佹紨绀烘埅鍥?| 鈽?|

### 1.2 Runtime 涓変欢濂楋紙璁蹭箟锛氱1鑺?Runtime锛?
| 鐭ヨ瘑鐐?| 璁蹭箟涓殑绮剧‘ API / 鍐欐硶 | 椤圭洰涓殑钀界偣 | 绾у埆 |
|---|---|---|---|
| Context锛堣繍琛屼笂涓嬫枃锛?| `@dataclass(frozen=True) class UserContext: user_id/tenant_id`锛涘伐鍏风鍚?`runtime: ToolRuntime[UserContext]`锛沗create_agent(..., context_schema=UserContext)`锛沗invoke(..., context=UserContext(...))` | 鐧诲綍鎬併€佺鎴枫€佹潈闄愭敞鍏ュ伐鍏凤紝鍓嶇涓嶄紶韬唤锛涚敓鍛藉懆鏈?鍗曟璋冪敤 | 鈽?|
| State锛堢煭鏈熻蹇嗭級 | `class CustomState(AgentState): ...`锛沗runtime.state.get("k", 0)`锛坉ict 涓嶈兘鐢ㄧ偣锛夛紱`state_schema=CustomState`锛涘伐鍏峰唴 `return Command(update={..., "messages":[ToolMessage(..., tool_call_id=runtime.tool_call_id)]})` | 涓氬姟瀛楁闅忎細璇濇祦杞紙鍒嗙被缁撴灉銆佸姩浣滃弬鏁般€佸鎵规剰瑙侊級 | 鈽?|
| Store锛堥暱鏈熻蹇嗭級 | `InMemoryStore()`锛堣涔夊彟鎻?PostgresStore/RedisStore锛夛紱`namespace` 鍏冪粍 + `key` 瀛楃涓?+ `value` dict锛沗runtime.store.get(ns,key)` / `put(ns,key,value)`锛沗store=` | 璺ㄤ細璇濈敤鎴峰亸濂姐€佸父鐢ㄤ骇鍝佺嚎銆佸巻鍙插喅绛?| 鈽?|
| 鐢熷懡鍛ㄦ湡宸紓 | Context 鍗曟 / State 鍚?thread_id / Store 璺?thread | 鏋舵瀯璁茶В銆侀潰璇曞繀闂?| 鈽?|

### 1.3 Middleware锛堣涔夛細绗?鑺?Middleware锛?
| 鐭ヨ瘑鐐?| 璁蹭箟涓殑绮剧‘ API / 鍐欐硶 | 椤圭洰涓殑钀界偣 | 绾у埆 |
|---|---|---|---|
| PII 鑴辨晱 | `PIIMiddleware("email", strategy="redact", detector=..., apply_to_input=, apply_to_output=)`锛涚瓥鐣?`block/redact/mask/hash` | 鎵嬫満鍙?閭/韬唤璇佽劚鏁忥紝鍚堣瀹℃煡 | 鈽?|
| 妯″瀷闄嶇骇 | `ModelFallbackMiddleware("涓绘ā鍨?, "澶囩敤妯″瀷")` | 涓绘ā鍨嬭秴鏃?闄愭祦鑷姩鍒囨崲锛屼繚鍙敤鎬?| 鈽?|
| 浜哄伐瀹℃牳 | `HumanInTheLoopMiddleware(interrupt_on={"send_email": {"description": ..., "allowed_decisions": ["approve","reject","edit"]}})`锛涙仮澶?`Command(resume={"decisions":[{"type":"reject","message":"璇皵澶功闈?}]})` | 鍙戦偖浠?閫€娆?寤哄崟鍓嶅鎵归棴鐜?| 鈽?|
| 鑷畾涔?node-style | `@before_agent` / `@before_model` / `@after_model` / `@after_agent`锛岀鍚?`(state, runtime) -> dict` | 璋冪敤璁℃暟銆侀檺娴併€佸姩鎬佹敞鍏ユ彁绀鸿瘝 | 鈽?|
| 鑷畾涔?wrap-style | `@wrap_model_call(request: ModelRequest, handler) -> ModelResponse`锛沗@wrap_tool_call` | 璁℃椂銆侀噸璇曘€佸紓甯稿厹搴曘€佸煁鐐?| 鈽?|
| 鑷畾涔夌被 | 缁ф壙 `AgentMiddleware`锛屾敞鍐屾椂浼犲疄渚?| 涓棿浠舵墦鍖呭鐢?| 鈽?|
| 楂樼骇鐢ㄦ硶 | `request.override(model_settings=...)` 鍔ㄦ€佹敼妯″瀷/宸ュ叿/鎻愮ず璇嶏紱`@hook_config(can_jump_to=["end"])` + 杩斿洖 `{"jump_to":"end"}` | 绠€鍗曢棶棰樼洿鎺ョ粨鏉熴€佸姩鎬侀€夋ā鍨?| 鈽?|

### 1.4 LangGraph锛堣涔夛細绗?鑺?鍩烘湰姒傚康銆佺2鑺?甯歌 WorkFlow銆佺3鑺?Think In LangGraph锛?
| 鐭ヨ瘑鐐?| 璁蹭箟涓殑绮剧‘ API / 鍐欐硶 | 椤圭洰涓殑钀界偣 | 绾у埆 |
|---|---|---|---|
| 鍥剧殑鍩烘湰瑕佺礌 | `StateGraph(State)`銆乣add_node`銆乣add_edge`銆乣START`/`END`銆乣compile()`锛汼tate 鐢?`TypedDict` | 涓讳笟鍔″浘 | 鈽?|
| Reducer | `Annotated[list[BaseMessage], add_messages]`銆乣Annotated[list[str], operator.add]`锛涗笉鍐?reducer 榛樿瑕嗙洊锛涘苟琛岃妭鐐瑰啓鍚屼竴瀛楁蹇呴』閰?reducer | 骞惰妫€绱㈢粨鏋滆仛鍚?| 鈽?|
| 鏉′欢杈逛笌璺敱 | `add_conditional_edges(node, router, mapping)`锛況outer 杩斿洖 `Literal[...]` | 鎰忓浘鍒嗘祦锛堢煡璇嗛棶绛?寤哄崟/闂茶亰锛?| 鈽?|
| Command | `return Command(update={...}, goto="next_node")`锛涜繑鍥炴敞瑙?`Command[Literal[...]]` | 鑺傜偣鍐呭喅绛?+ 鐘舵€佹洿鏂颁竴姝ュ畬鎴愶紙鏈€灏忚竟锛?| 鈽?|
| 6 绉嶇紪鎺掓ā寮?| Prompt Chaining锛堝惈楠岃瘉 Gate锛夈€丳arallelization銆丷outing銆丱rchestrator-Worker + `Send`銆丒valuator-Optimizer锛堝甫杩唬涓婇檺锛夈€丼ubgraphs | 閫夊瀷涓庡姣斿疄楠?| 鈽?|
| Send API | `[Send("worker", {"section": s}) for s in state["sections"]]` + `add_conditional_edges("orchestrator", assign_workers, ["worker"])` | 鎵归噺宸ュ崟鎽樿 / 鏃ユ姤鐢熸垚锛屽瓙浠诲姟鏁颁笉纭畾 | 鈽?|
| DeepResearcher 鍒嗗眰 | planner 鐢?`with_structured_output(Sections)`锛涚埗 State `completed_sections: Annotated[list, operator.add]`锛泂ynthesizer 鐢?`"\n\n---\n\n".join(...)` | 鎶ュ憡鐢熸垚妯″潡 | 鈽?|
| 瀛愬浘 | `add_node("retrieve", 宸茬紪璇戝瓙鍥?` 鐩存帴宓屽叆锛堝叡浜?key 鑷姩鏄犲皠銆乮nterrupt 鍐掓场锛夛紱鎴栨櫘閫氳妭鐐瑰唴 `subgraph.invoke()` 鎵嬪姩鏄犲皠锛沗graph.get_graph(xray=True)` | 妫€绱㈣兘鍔涘鐢ㄥ埌澶氭潯涓氬姟绾?| 鈽?|
| 涓柇涓庢仮澶?| 鑺傜偣鍐?`interrupt({...})`锛沗response["__interrupt__"][0].value`锛沗invoke(Command(resume={...}), config)`锛?*蹇呴』鎸?checkpointer** | 浜哄伐瀹℃壒銆佷俊鎭ˉ鍏?| 鈽?|
| 绋冲畾鎬?| `retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0)`锛沗TimeoutPolicy` / `CachePolicy` | 澶栭儴 API/妯″瀷璋冪敤鍏滃簳 | 鈽?|
| 棰勭疆浠?| `ToolNode(tools)`銆乣tools_condition`锛沗create_agent` 搴曞眰=llm 鑺傜偣 + tools 鑺傜偣 + 鏉′欢杈?+ compile | 鎵嬪啓 Agent銆佽娓呭師鐞?| 鈽?|
| 璁捐鏂规硶璁?| 鍏堢敾鍥惧啀鍐欎唬鐮侊紱鍥涚被鑺傜偣鑱岃矗锛圠LM / Data / Action / Human锛夛紱State 鍙斁涓嬫父鍐崇瓥瑕佺敤鐨勫瓧娈碉紱鏈€灏忚竟鍘熷垯锛涘紓甯稿垎绾э紙閲嶈瘯 / 鍐欏洖 State / `interrupt()` / 鎶涘嚭锛?| 璁捐璇勫銆侀潰璇?| 鈽?|

### 1.5 Multi-Agent锛堣涔夛細绗?鑺?Multi Agent锛?
| 鐭ヨ瘑鐐?| 璁蹭箟涓殑绮剧‘ API / 鍐欐硶 | 椤圭洰涓殑钀界偣 | 绾у埆 |
|---|---|---|---|
| 鍥涚妯″紡 | **Subagents**锛堜富 Agent 鎶婂瓙 Agent 褰?Tool锛? **Handoffs**锛堟敼 state 瑙﹀彂璺敱锛? **Skills**锛堟寜闇€鍔犺浇锛? **Router**锛堝厛鍒嗙被鍐嶅垎鍙戯紝鏈熬姹囨€伙級锛涘姣旂淮搴︼細鍒嗗竷寮忓紑鍙戙€佸苟琛屻€佸璺炽€佺洿鎺ヤ氦浜?| 閫夊瀷锛岄伩鍏?涓哄鑰屽" | 鈽?|
| Subagent 钀藉湴 | `@tool` 鍐呰 `runtime.state`銆佹嫾 `HumanMessage`銆乣await 瀛恆gent.ainvoke({...})`銆佽繑鍥?`['messages'][-1].content`锛涗富 Agent `create_agent(tools=[...], state_schema=...)` | 涓撳鍥紙閫€娆句笓瀹?鎶€鏈帓闅滀笓瀹讹級 | 鈽?|
| 鍘熷垯 | 浼樺厛鍗?Agent锛涘彧鏈夊湪涓婁笅鏂囬殧绂汇€佸洟闃熷垎宸ャ€佸苟琛屾敹鐩婃槑鏄炬椂鎵嶆媶 | 闈㈣瘯蹇呴棶 | 鈽?|

### 1.6 RAG锛堣涔夛細绗?鑺?RAG Agent锛?
| 鐭ヨ瘑鐐?| 璁蹭箟涓殑绮剧‘ API / 鍐欐硶 | 椤圭洰涓殑钀界偣 | 绾у埆 |
|---|---|---|---|
| 鏂囨。鍔犺浇 | `BaseLoader.load() -> list[Document]`锛沗PyPDFLoader(file_path=..., mode="page"/"single")`锛沗MinerULoader(source=..., mode="flash"/"precision", ocr=True).load()`锛汼DK锛歚MinerU(token=...)`銆乣client.flash_extract/extract`銆乣result.markdown` | 鐭ヨ瘑搴撳綍鍏ワ紙鎵弿浠?琛ㄦ牸璧?MinerU OCR锛?| 鈽?|
| 鏂囨湰鍒囧垎 | `CharacterTextSplitter(separator, chunk_size, chunk_overlap)`锛沗from_tiktoken_encoder(encoding_name="cl100k_base")`锛沗RecursiveCharacterTextSplitter(separators=["\n\n","\n","銆?])`锛沗MarkdownHeaderTextSplitter(headers_to_split_on=[("#","h1"),...], strip_headers=False)` | 妫€绱㈣川閲忕殑鍦板熀锛涚粨鏋勬劅鐭ュ垏鍒嗕繚鐣?h1/h2/h3 鍏冩暟鎹?| 鈽?|
| 鍒囧垎缁忛獙鍊?| chunk_size 200鈥?000銆乷verlap 10%鈥?0%銆佹绱?k 3鈥?0 | 璋冨弬瀹為獙锛堢畝鍘嗗彲鍐欏姣旀暟鎹級 | 鈽?|
| 鍚戦噺鍖?| `OllamaEmbeddings(model="qwen3-embedding:0.6b", dimensions=1024)`锛沗DashScopeEmbeddings(model="text-embedding-v4")` | 鏈湴寮€鍙?/ 浜戠鐢熶骇涓ゅ | 鈽?|
| 鍚戦噺搴擄紙寮€鍙戞湡锛?| `InMemoryVectorStore(embedding=...)`锛沗add_documents` / `delete` / `similarity_search_with_score(query, k=5)` / `filter` / `score_threshold` | 鍗曞厓娴嬭瘯銆佸洖褰掓祴璇?| 鈽?|
| 涓ょ鏋舵瀯 | **2-Step RAG**锛歚@dynamic_prompt` 鍐呭厛妫€绱㈠啀鎷肩郴缁熸彁绀猴紱**Agentic RAG**锛歚@tool def retrieve_docs(query)` 浜ょ粰 Agent 鍐冲畾浣曟椂妫€绱€佸彲澶氭妫€绱紱鍙︽湁 Hybrid锛堢敓鎴愬悗楠岃瘉锛?| 鍋氭垚鍙垏鎹㈠紑鍏筹紝A/B 瀵规瘮锛堢畝鍘嗕寒鐐癸級 | 鈽?|
| 婧簮 | `Document.page_content` + `metadata`锛坔1/h2/h3銆乻ource銆乨oc_id锛夛紱妫€绱㈢粨鏋滃洖浼犲墠绔仛寮曠敤鍗＄墖 | 骞昏娌荤悊銆佸彲淇″害 | 鈽?|

### 1.7 Milvus锛堣涔夛細绗?鑺?Milvus 鍚戦噺搴擄級

| 鐭ヨ瘑鐐?| 璁蹭箟涓殑绮剧‘ API / 鍐欐硶 | 椤圭洰涓殑钀界偣 | 绾у埆 |
|---|---|---|---|
| 杩炴帴涓庨儴缃?| `MilvusClient(uri="http://host:19530")`锛汥ocker Compose 閮ㄧ讲 Standalone锛汫UI 鐢?attu锛?000 绔彛锛?| 鐢熶骇鍚戦噺搴?| 鈽?|
| Schema | `client.create_schema(auto_id=False, enable_dynamic_field=False)`锛沗DataType.INT64/FLOAT_VECTOR(dim=1024)/SPARSE_FLOAT_VECTOR/VARCHAR(max_length, enable_analyzer=True, analyzer_params={"type":"chinese"})` | 鐭ヨ瘑搴?collection 璁捐 | 鈽?|
| 鍐呯疆 BM25 | `Function(name="text_bm25_emb", input_field_names=["content"], output_field_names=["sparse"], function_type=FunctionType.BM25)` + `schema.add_function(...)` | 绋€鐤忔绱㈠厤棰濆妯″瀷 | 鈽?|
| 绱㈠紩 | `prepare_index_params()` + `add_index(field_name=..., index_type="AUTOINDEX"/"HNSW"/"IVF_FLAT"/"SPARSE_INVERTED_INDEX"/"INVERTED"/"BITMAP", metric_type="COSINE"/"IP"/"L2"/"BM25")` | 鎬ц兘涓庡彫鍥炴潈琛?| 鈽?|
| 鏁版嵁鎿嶄綔 | `insert` / `upsert` / `delete` / `search(anns_field, data, limit, filter, output_fields, search_params)`锛涚‖绾︽潫锛歭imit+offset 鈮?16384銆乵etric 蹇呴』涓庣储寮曚竴鑷淬€乣ids` 涓?`data` 浜掓枼 | 鐭ヨ瘑搴?CRUD | 鈽?|
| 娣峰悎妫€绱?| `AnnSearchRequest(data=[...], anns_field="dense", param={"metric_type":"COSINE"}, limit=3, filter=...)` 脳 绋犲瘑/绋€鐤?+ `client.hybrid_search(collection_name=..., reqs=..., ranker=..., limit=..., output_fields=[...])`锛沗WeightedRanker(0.5,0.5)` / `RRFRanker(k=60)`锛?/(k+rank)锛夛紱鍔犳潈鍓嶉渶 Min-Max / Z-Score / Softmax 褰掍竴鍖?| 鍙洖鐜囨彁鍗囨牳蹇?| 鈽?|
| 绮炬帓 | `Function(name="dashscope_semantic_ranker", input_field_names=["content"], function_type=FunctionType.RERANK, params={"reranker":"model","provider":"ali","model_name":"gte-rerank-v2","queries":[query]})`锛涗袱闃舵锛氬厛 fetch_k 鍒濈瓫鍐?rerank 鍒?k | 鍑嗙‘鐜囨彁鍗囨牳蹇冿紙璐碉紝鍙鍊欓€夊仛锛?| 鈽?|
| 杩囨护 | 琛ㄨ揪寮?`'h2 == "..."'`銆乣'title like "%...%"'`銆乣'id in [1,2]'` | 绉熸埛/鏂囨。鑼冨洿鐨勭‖闅旂锛屽厛杩囨护鍐嶆绱?| 鈽?|
| LangChain 闆嗘垚 | `from langchain_milvus import Milvus, BM25BuiltInFunction`锛沗Milvus(embeddings, collection_name=..., builtin_function=BM25BuiltInFunction(analyzer_params={"type":"chinese"}), vector_field=["dense","sparse"], connection_args={"uri":...}, drop_old=...)`锛沗similarity_search_with_score(query, k=, ranker_type="weighted"/"rrf", ranker_params={"weights":[0.4,0.6]}/{"k":60}, expr=..., fetch_k=5, reranker=...)` | 涓氬姟浠ｇ爜鐩存帴璋冪敤 | 鈽?|
| 灞€闄?| LangChain 灏佽涓嬫贩鍚堟绱㈠彧鏀寔绋€鐤?绋犲瘑銆佷笉鏀寔澶氭ā鎬侊紱鏈夌█鐤忓悜閲忔椂榛樿璧版贩鍚堟绱紝蹇呴』浼?ranker 鍙傛暟 | 闈㈣瘯缁嗚妭 | 鈽?|

### 1.8 MCP锛堣涔夛細绗?鑺?MCP锛?
| 鐭ヨ瘑鐐?| 璁蹭箟涓殑绮剧‘ API / 鍐欐硶 | 椤圭洰涓殑钀界偣 | 绾у埆 |
|---|---|---|---|
| 鏍稿績姒傚康 | MCP Server锛堟彁渚涙柟锛? MCP Client锛堣鏈嶅姟涓庡伐鍏凤級/ MCP Host锛圓gent锛夛紱浼犺緭锛歚stdio`锛堝瓙杩涚▼銆佹棤缃戠粶寤惰繜锛塿s `streamable_http`锛圫SE 鐨?HTTP 褰㈡€侊級 | 璁叉竻"涓轰粈涔?MCP 涓嶆槸鍙堜竴涓?RPC" | 鈽?|
| 鎺ュ閮ㄦ湇鍔?| `MultiServerMCPClient({"time": {"transport":"stdio","command":"uvx","args":[...]}})` 鎴?`{"transport":"http","url":...}`锛沗tools = await client.get_tools()`锛涘伐鍏锋槸寮傛鐨?鈫?`agent.ainvoke` | 鑸彮/澶╂皵/鏃堕棿/鎼滅储 | 鈽?|
| 鑷畾涔夋湇鍔?| `uv add fastmcp`锛沗mcp = FastMCP("Math")`锛沗@mcp.tool()`锛堝繀椤伙級/ `@mcp.resources` / `@mcp.prompt`锛沗mcp.run(transport="stdio")` | 鎶婁紒涓氬瓨閲忕郴缁?MCP 鍖栵紙宸紓鍖栦寒鐐癸級 | 鈽?|

### 1.9 璇剧▼宸茬粰鍒扮殑宸ョ▼鍖栵紙鍙洿鎺ュ鐢級

- **FastAPI 涓夋帴鍙?*锛歚POST /chat/stream`锛坄StreamingResponse(..., media_type="text/event-stream")`锛夈€乣GET /chat/messages?thread_id=`銆乣DELETE /chat/messages?thread_id=`锛屽鍔?OSS 鍓嶇鐩翠紶绛惧悕 URL 鎺ュ彛銆?- **鐩綍鍒嗗眰**锛歚app/main.py`銆乣api/v1/{chat,oss}.py`銆乣models/schemas.py`銆乣common/logger.py`銆乣agents/*.py`銆乣db/`銆?- **閰嶇疆涓庡瘑閽?*锛歚uv` 绠′緷璧栥€乣.env` + `load_dotenv`銆丏ashScope/Tavily/OSS 鐨?Key 鍏ㄩ儴璧扮幆澧冨彉閲忋€?- **LangSmith**锛氱幆澧冨彉閲忓紑 tracing锛沗langgraph dev` + `langgraph.json`锛坄graphs` 鍐欐硶 `[Agent鏂囦欢璺緞]:[Agent鍙橀噺鍚峕`锛夋媺璧?2024 绔彛鐨勮皟璇曟湇鍔★紝閰嶅悎 LangSmith Studio 鑱旇皟銆?- **鎸佷箙鍖?*锛歚SqliteSaver` + `setup()`锛宍delete_thread(thread_id)` 娓呯┖锛宍checkpointer.get(...)["channel_values"]["messages"]` 璇诲巻鍙层€?- **瀵硅薄瀛樺偍**锛歄SS 寮€閫?RAM 瀛愯处鍙?鍏叡璇?+ CORS锛堣涔夋槑纭細鐢熶骇搴旂鏈?+ CDN锛夈€?
### 1.10 杩橀渶瑕佽ˉ鐨勫伐绋嬭兘鍔涳紙浼佷笟绾ч」鐩繀椤绘湁锛屾瘡椤?2鈥? 澶╁彲涓婃墜锛?
| 缂哄彛 | 瑕佽ˉ鍒颁粈涔堢▼搴?| 涓轰粈涔堝繀椤?|
|---|---|---|
| FastAPI 宸ョ▼鍖?| Router 鍒嗗眰銆乣Depends` 渚濊禆娉ㄥ叆銆佸叏灞€寮傚父銆丆ORS銆丣WT + RBAC銆丱penAPI 鏂囨。 | 璇剧▼鍙粰浜?3 涓帴鍙ｇ殑 Demo 绾у啓娉?|
| 鏁版嵁搴?| SQLAlchemy 2.x + Alembic锛汸ostgreSQL锛堜細璇?宸ュ崟/瀹℃壒/璇勬祴锛夛紱Redis锛堢紦瀛樸€侀檺娴併€佷細璇濋攣锛?| Checkpointer 涔嬪鐨勪笟鍔℃暟鎹鏈夊湴鏂硅惤 |
| 寮傛浠诲姟 | ARQ / Celery / FastAPI BackgroundTasks锛氭枃妗ｈВ鏋愩€佹壒閲忚瘎娴嬨€佹棩鎶ョ敓鎴?| 鏂囨。鍏ュ簱鍑犲崄绉掞紝涓嶈兘闃诲璇锋眰 |
| SSE 缁嗚妭 | 浜嬩欢绫诲瀷锛坄token` / `tool` / `interrupt` / `done`锛夈€佸績璺炽€佹柇绾块噸杩?| 鍓嶇浣撻獙涓庣ǔ瀹氭€?|
| Vue3 鍓嶇 | Vite + TS + Pinia + Element Plus銆丼SE 娓叉煋銆丮arkdown/浠ｇ爜楂樹寒銆佸鎵逛笌宸ュ崟琛ㄦ牸 | 浣犵殑鍓嶇鑳藉姏瑕佸彉鎴?AI 浜や簰鐣岄潰"鐨勫姞鍒嗛」 |
| 閮ㄧ讲 | Docker Compose锛坅pi / web / milvus / attu / postgres / redis锛夈€丯ginx銆丟itHub Actions | 闈㈣瘯瀹樼湅 README 绗竴鐪煎氨鏄?鑳戒笉鑳借窇璧锋潵" |
| 娴嬭瘯涓庤瘎娴?| pytest + httpx锛汱angSmith dataset + evaluators锛沢olden set 50鈥?00 鏉?| 绠€鍘嗛噷鎵€鏈?鎻愬崌 xx%"鐨勬暟瀛楅兘鏉ヨ嚜杩欓噷 |
| 鎴愭湰涓庡畨鍏?| token 缁熻銆佹ā鍨嬭矾鐢便€佺紦瀛樸€侀檺娴併€佸璁℃棩蹇?| 浼佷笟绾?鈮?鑳借窇锛岃€屾槸"鏁笂绾? |

---

## 2. 浠庣煡璇嗙偣鍒扮畝鍘嗭細涓夋。娓呭崟

### 2.1 蹇呭啓锛堢己涓€椤癸紝椤圭洰灏变細琚潰璇曞畼褰掔被涓?璇剧▼ Demo"锛?
1. **鎵嬪啓 LangGraph 涓诲浘**锛歚StateGraph` + 鑷畾涔?State/Reducer + `Command` 璺敱 + 瀛愬浘澶嶇敤锛堜笉鏄彧璋?`create_agent`锛夈€?2. **HITL 瀹℃壒闂幆**锛歚interrupt()` + 鎸佷箙鍖?checkpointer + 鍓嶇瀹℃壒椤?+ `Command(resume=...)` 鎭㈠銆?3. **Milvus 娣峰悎妫€绱?*锛氱瀵?+ BM25 绋€鐤?+ RRF 铻嶅悎 + Cross-Encoder 绮炬帓 + 鍏冩暟鎹繃婊ゃ€?4. **缁撴瀯鎰熺煡鍒囧垎 + 婧簮**锛歚MarkdownHeaderTextSplitter` 淇濈暀 h1/h2/h3锛屾绱㈢粨鏋滃甫寮曠敤銆?5. **SSE 娴佸紡**锛歵oken 閫愬瓧 + 宸ュ叿璋冪敤杩涘害 + 涓柇浜嬩欢锛屽墠绔兘涓€旀帴绠°€?6. **澶氱鎴?Context**锛歚ToolRuntime[UserContext]` 娉ㄥ叆 `tenant_id/user_id`锛屾绱晶 `filter` 纭殧绂汇€?7. **Middleware 涓変欢濂?*锛歅II 鑴辨晱 + 妯″瀷闄嶇骇 + 鎽樿鍘嬬缉锛堟湁浠ｇ爜銆佹湁寮€鍏筹級銆?8. **LangSmith 璇勬祴**锛氳嚦灏戜竴濂?golden set + Recall@K / 寮曠敤鍑嗙‘鐜?/ 涓€娆￠€氳繃鐜囷紝README 閲屾斁鎶ュ憡銆?
### 2.2 鍔犲垎锛堣浣犱粠"鍚堟牸"鍒?浜溂"锛?
- `Send` 鍔ㄦ€佸苟琛岋紙鎵归噺宸ュ崟鎽樿/鏃ユ姤锛夛紝鍓嶇杩涘害鏉℃寜 worker 鎺ㄨ繘銆?- 鑷缓 **MCP Server**锛堟妸鍐呴儴璁㈠崟/CRM/鍙 SQL 灏佽锛夛紝Agent 鍔ㄦ€佹寕杞藉伐鍏枫€?- **Agentic RAG 涓?2-Step RAG 鍙垏鎹?*锛岀敤鍚屼竴璇勬祴闆嗙粰鍑哄姣旀暟鎹€?- **Evaluator-Optimizer** 鍥炵幆锛堢敓鎴?鈫?璇勫垎 鈫?涓嶈揪鏍囧甫鍙嶉閲嶅啓锛屾渶澶?3 杞級銆?- **Store 闀挎湡璁板繂**锛堣法浼氳瘽鍋忓ソ锛夛紝浠ュ強 Summarization 鍘嬬缉鍓嶅悗鐨勬垚鏈姣斻€?- **Multi-Agent** 涓撳鍥紙Subagents 妯″紡锛夛紝骞惰鏄?涓轰粈涔堜笉鏄崟 Agent"銆?- 鍓嶇"**宸ヤ綔娴佸彲瑙嗗寲**"椤碉細`graph.get_graph(xray=True)` 瀵煎嚭 Mermaid锛屽睍绀烘瘡涓妭鐐硅€楁椂銆?- **鎴愭湰/寤惰繜浼樺寲**锛氭ā鍨嬭矾鐢憋紙闅鹃棶棰樿蛋澶фā鍨嬶級銆佺紦瀛樸€佸苟鍙戙€乼oken 缁熻銆?- **A/B 瀹為獙**锛歊RF vs Weighted銆佹湁鏃?rerank銆乧hunk 500 vs 800锛屽悇缁欎竴缁勬暟鎹€?
### 2.3 浜嗚В鍗冲彲锛堣兘璁叉竻鍘熺悊锛屼笉涓€瀹氳鍐欙級

`MemorySaver` 瀹舵棌閫夊瀷锛圛nMemory/Sqlite/Postgres锛夈€丮ilvus 鍚勭储寮曞師鐞嗭紙HNSW/IVF_FLAT锛夈€佸綊涓€鍖栨柟娉曪紙Min-Max/Z-Score/Softmax锛夈€丮CP 鍗忚鎶ユ枃銆丏eep Agents銆丩angGraph 鐨?`CachePolicy`/`TimeoutPolicy`銆?
---

## 3. 瀹氱鏂瑰悜锛氫紒涓氬唴閮ㄦ湇鍔″彴锛圫martDesk AI锛?
> 杩欎竴鐗堝彧淇濈暀涓€涓柟鍚戙€侭/C/D/E 鍥涗釜澶囬€夛紙浼佷笟鐭ヨ瘑搴?Copilot銆佸 Agent 琛岀▼銆佸妯℃€侀ギ椋熴€丮CP 宸ュ叿缃戝叧锛夊凡鍒犻櫎鈥斺€旀柟鍚戣秺澶氳秺鍐欎笉涓嬪幓锛岀畝鍘嗕笂涔熷彧鑳芥斁涓€涓富椤圭洰銆?
### 3.1 涓€鍙ヨ瘽瀹氫綅

鍏徃鍐呴儴鍛樺伐鐢ㄨ嚜鐒惰瑷€鎻愰棶鎴栨彁闇€姹傦紝Agent 瑕佷箞缁欏嚭**甯﹀紩鐢ㄧ殑绛旀**锛岃涔堢敓鎴?*涓€寮犲緟鏈汉纭鐨勫伐鍗?*锛岃涔堝仠鍦?*浜哄伐瀹℃壒**绛夋湁鏉冮檺鐨勪汉鐐瑰ご銆?
### 3.2 涓氬姟闂幆锛堝氨鏄憳宸ョ湡瀹炰細閬囧埌鐨勫洓浠朵簨锛?
| 鍛樺伐璇翠粈涔?| Agent 璧板摢鏉¤矾 | 鏈€鍚庡彂鐢熶粈涔?|
|---|---|---|
| "鍙戠エ鎬庝箞寮€锛? / "骞村亣澶氬皯澶╋紵" | 妫€绱㈢煡璇嗗簱 鈫?甯?`[1][2]` 寮曠敤浣滅瓟 | 绉掑洖锛岀瓟妗堝彲婧簮锛涙病妫€绱㈠埌灏辫鎬傚苟缁欎笅涓€姝?|
| "甯垜寤轰釜宸ュ崟锛歏PN 杩炰笉涓? | 鎶藉彇鍙傛暟 鈫?**纭鍗?*锛堟彁鍗曚汉涓€閿級 | 寤哄崟鎴愬姛锛屽崟鍙峰洖濉紝閫氱煡杩愮淮 |
| "鎶?TK-鈥?鍏虫帀锛岄『渚块€氱煡鎻愬崟浜? | 椋庨櫓鍗囩骇 鈫?**瀹℃壒**锛堝憳宸ュ彲鍙戣捣锛屼富绠＄偣澶达級 | 鍏冲崟 + 閫氱煡锛涘憳宸ヨ嚜宸辫兘鍙戣捣锛屼絾鍙湁涓荤鍦?resume 閭ｅ埢鐨勮韩浠借兘鐐归€氳繃 |
| "甯垜鎶婂伐鍗曞叧鎺?锛堟病璇村崟鍙凤級 | 缂哄弬鏁?鈫?**婢勬竻**锛圓I 鍙嶉棶锛?| 琛ヤ竴鍙ュ崟鍙凤紝閲嶆柊杩涚‘璁?|

### 3.3 涓轰粈涔堣繖涓柟鍚戞渶閫傚悎"瀹炰範/鏍℃嫑绠€鍘?

1. **闈㈣瘯瀹樹竴鍚氨鎳?*锛欼T 鏈嶅姟鍙版槸姣忎釜鍏徃閮芥湁鐨勯儴闂紝"闂埗搴?+ 鎻愬伐鍗?+ 瑕佸鎵? 涓嶉渶瑕佽В閲婁笟鍔¤儗鏅€?2. **澶╃劧瑕嗙洊浼佷笟绾х壒寰?*锛氬绉熸埛锛堥泦鍥㈠瀛愬叕鍙革級銆佹潈闄愶紙鍛樺伐/涓荤/鐭ヨ瘑搴?owner锛夈€佸璁★紙璋佹壒鐨勩€佽皝鎵ц鐨勶級銆佸彲鎾ら攢涓庝笉鍙挙閿€鍔ㄤ綔鍒嗙骇鈥斺€旇繖浜涙槸"璇剧▼ Demo"娌℃湁鐨勩€?3. **鑳芥妸榛戦┈鐨勭煡璇嗙偣鍏ㄧ敤涓?*锛歀angGraph 涔濊妭鐐?+ `interrupt`/`resume` + checkpointer 鎸佷箙鍖栥€丷untime Context 娉ㄥ叆绉熸埛韬唤銆丗astMCP + `MultiServerMCPClient` 宸ュ叿鍖栥€丮ilvus 绋犲瘑 + 鍐呯疆 BM25 娣峰悎妫€绱€佺粨鏋勫寲杈撳嚭銆?4. **鍙紨绀?*锛欳LI 涓€鏉″懡浠ゅ氨鑳界幇鍦鸿窇鍑?鏆傚仠 鈫?鎹釜杩涚▼鎭㈠"锛屾瘮浠讳綍 PPT 閮芥湁璇存湇鍔涖€?
### 3.4 涓?璇剧▼椤圭洰锛圓I 绉佸帹锛?鐨勫樊鍒紙闈㈣瘯蹇呰瀵规瘮锛?
| 缁村害 | 璇剧▼椤圭洰 | 杩欎釜椤圭洰 |
|---|---|---|
| 缂栨帓 | 鍗?Agent + 宸ュ叿 | 涔濊妭鐐逛富鍥?+ 涓夐椄闂紝璺敱闆嗕腑鍦?`graph.py` 鐨?4 涓?`route_*` |
| 浜虹殑浠嬪叆 | 涓€鏉?`HumanInTheLoopMiddleware` | 涓夌浜哄垎寮€锛氭緞娓?/ 纭锛堟彁鍗曚汉锛? 瀹℃壒锛堟湁鏉冮檺鐨勪汉锛?|
| 妫€绱?| 鍗曡矾鍚戦噺妫€绱?| Milvus 绋犲瘑 + BM25 鍙岃矾锛屾湇鍔＄ RRF锛屽甫寮曠敤涓?娌″懡涓氨璁ゆ€? |
| 宸ュ叿 | 杩涚▼鍐呭嚱鏁?| 2 涓?FastMCP server / 9 涓伐鍏凤紙宸ュ崟 5 + 鐭ヨ瘑 2 + 娌荤悊 2锛夛紝stdio 涓庤繘绋嬪唴鍙屼紶杈?|
| 瀹℃壒钀借处 | 鏃狅紙瀹℃壒鍙湪鍐呭瓨/涓柇閲岋級 | approvals 涓€寮犺〃锛堝鎵?4 鎬佺姸鎬佹満锛夛紝瀹℃壒涓績鍙煡 |
| 鎸佷箙鍖?| 杩涚▼鍐呮垨 SQLite | PostgresSaver锛岃法杩涚▼璺ㄩ噸鍚仮澶?|
| 鏁版嵁闅旂 | 鏃?| 绉熸埛鍦ㄥ绉熸埛涓婁笅鏂?+ 妫€绱?filter 鍙屽眰杩囨护 |

### 3.5 鑼冨洿杈圭晫锛堝仛浠€涔?/ 涓嶅仛浠€涔堬級

**鍋?*锛氬憳宸ユ彁闂€佺煡璇嗗簱妫€绱笌寮曠敤銆佸伐鍗曞叏鐢熷懡鍛ㄦ湡锛堝缓/鏀?鍏?鏌ワ級銆佷笁绉嶄汉宸ヤ粙鍏ャ€佸绉熸埛銆丮CP 宸ュ叿鍖栥€佹寔涔呭寲銆?
**涓嶅仛**锛堝苟涓旇鑳借В閲婁负浠€涔堜笉鍋氾級锛?- 涓嶅仛瀵瑰瀹㈡湇鈥斺€旈偅浼氭妸"鍐呴儴鍒跺害鐭ヨ瘑搴?鍜?瀵瑰璇濇湳"娣峰湪涓€璧凤紝璇箟涓嶈嚜娲斤紱
- 涓嶅仛鍙戠エ/璐㈠姟鍩熲€斺€旈偅鏄?ERP 鐨勫湴鐩橈紝纭杩涙潵鍙細琚拷闂?浣犵湡瀵规帴浜嗗摢浜涚郴缁?锛?- 涓嶅仛澶?Agent 涓撳鍥⑩€斺€斿崟绾跨▼涓氬姟娴佺▼鎷嗘垚澶?Agent 鍙鍚屾鎴愭湰锛堣涔夊師璇濓細浼樺厛鍗?Agent锛夛紱
- 涓嶅仛鍓嶇澶у睆/鐐妧鍔ㄧ敾鈥斺€旂簿鍔涙寜 Agent 70% / FastAPI 20% / Vue 10% 鍒嗛厤銆?
### 3.6 闈㈣瘯涓€鍙ヨ瘽

> "鎴戝仛鐨勬槸浼佷笟鍐呴儴鏈嶅姟鍙?Agent銆傚畠鐨勫叧閿笉鏄妸鐭ヨ瘑搴撴帴杩涙ā鍨嬶紝鑰屾槸鎶?*鍔ㄤ綔**鍜?*鍥炵瓟**鍒嗗紑锛氬洖绛斿彧璐熻矗甯﹀紩鐢紱鍔ㄤ綔瑕佸垎绾р€斺€斿彲鎾ら攢鐨勮鎻愬崟浜虹‘璁わ紝涓嶅彲鎾ら攢鎴栧澶栫殑蹇呴』鍋滃湪瀹℃壒銆傛墍浠ュ浘涓婃湁涓€涓節鑺傜偣涓诲浘銆佷笁鎵囦汉绫婚椄闂紝9 涓伐鍏峰叏閮ㄨ蛋 MCP锛屽鎵硅惤鍦ㄦ湇鍔＄涓€寮犺〃閲岋紙涓嶆槸鍙椿鍦?checkpoint锛夛紝鐘舵€佸瓨鍦?Postgres锛岃繘绋嬫潃鎺夋崲涓繘绋嬭繕鑳芥帴鐫€鎵广€?

## 4. SmartDesk-Agent 璇︾粏璁捐锛堜笌褰撳墠浠ｇ爜涓€涓€瀵瑰簲锛?
### 4.1 椤圭洰鍚嶇墖锛堝彲鐩存帴鐢ㄧ殑绠€鍘嗘爣棰橈級

- **椤圭洰鍚?*锛歋martDesk AI 鈥斺€?浼佷笟鍐呴儴鏈嶅姟鍙?Agent 骞冲彴
- **涓€鍙ヨ瘽**锛氬憳宸ョ敤鑷劧璇█鎻愰渶姹傦紝Agent 瑕佷箞缁欏嚭**甯﹀紩鐢ㄧ殑绛旀**锛岃涔堢敓鎴?*寰呯‘璁ょ殑宸ュ崟鍙傛暟锛堢‘璁ゅ崱锛?*锛岃涔堝仠涓嬬瓑**鏈夋潈闄愮殑浜哄鎵?*銆?- **鎶€鏈叧閿瘝**锛歀angGraph锛堜節鑺傜偣 + 涓夐椄闂?+ 鏄惧紡璺敱锛夈€丩angChain 1.x銆丮CP锛團astMCP 脳 2 server / 9 宸ュ叿锛夈€丮ilvus锛坉ense + 鍐呯疆 BM25 + 鏈嶅姟绔?RRF锛夈€丳ostgreSQL锛坈heckpoint + 涓氬姟琛?+ 瀹℃壒/瀹¤琛級銆丗astAPI + SSE锛堟祦寮?+ interrupt 浜嬩欢锛夈€乂ue3锛堜笅涓€姝ワ級
- **椤圭洰瀹氫綅**锛氫腑灏忓巶 AI 搴旂敤 / Agent 瀹炰範鎴栧垵绾у矖浣嶏紝"鑳芥紨绀恒€佽兘璁叉竻鍙栬垗銆佹湁鐪熷疄鏁板瓧"姣斿爢妗嗘灦鏇撮噸瑕併€?
### 4.2 绯荤粺鏋舵瀯锛堝綋鍓嶇湡瀹炵粨鏋勶級

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€ 鍏ュ彛锛堢幇鍦?/ 涓嬩竴姝ワ級鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?CLI: scripts/run_graph.py锛坮un / resume / state / graph / tools / chat / approvals / audit锛?鈹?璺熻: scripts/trace_run.py锛堥€愯妭鐐规墦鍗?鍐欎簡鍝簺瀛楁"锛?鈹?HTTP/SSE: backend/app/api锛?api/v1/chat/stream銆?runs/{id}銆?runs/{id}/resume銆?approvals銆?audit锛?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?                           鈹?get_graph() 鈫?invoke(initial_state, config, context)
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈻尖攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?LangGraph 涓诲浘锛坆ackend/app/agents/graph.py锛?44 琛岋級           鈹?鈹?9 鑺傜偣 + 5 涓矾鐢卞嚱鏁?+ 3 涓?interrupt 闂搁棬                      鈹?鈹斺攢鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?   鈹?         鈹?             鈹?             鈹?knowledge.py  tools/mcp_client  checkpoint.py  rag/vector_store.py
   鈹?         鈹?             鈹?             鈹?Milvus:19530  2脳FastMCP server  PG鈫扴QLite 鍏滃簳  PostgreSQL 16
```

### 4.3 涓诲浘锛氫節鑺傜偣 + 涓夐椄闂紙褰撳墠浠ｇ爜锛?
鑺傜偣鍚嶅叏閮ㄦ槸鍔ㄨ瘝鐭锛岃鍥惧儚璇诲彞瀛愶細

```
classify_request 鈫?gather_evidence 鈫?answer_with_citations 鈫?compose_reply   锛堢煡璇嗗瀷锛屼笉鍋滐級
                                  鈫?plan_action
                                        鈹?ask_missing_info  鈫?plan_action     锛堢己鍙傛暟锛宨nterrupt锛?                                        鈹?confirm_action    鈫?execute_action  锛堝彲鎾ら攢锛宨nterrupt锛?                                        鈹?       鈹旓紙纭鏃舵敼鍑轰笉鍙€嗗弬鏁?鈫?閲嶇畻椋庨櫓锛夆啋 approve_action
                                        鈹?approve_action    鈫?execute_action  锛堜笉鍙€?鍏ㄥ憳鍙锛宨nterrupt锛?                                                      execute_action 鈫?compose_reply
```

璺敱鍙湁涓€涓湴鏂光€斺€擿backend/app/agents/graph.py` 閲屼簲涓函鍑芥暟锛?
| 璺敱鍑芥暟 | 鍒ゆ柇渚濇嵁 | 鍘诲悜 |
|---|---|---|
| `route_after_classify` | `intent == "chat"` | `compose_reply`锛涘惁鍒?`gather_evidence` |
| `route_after_gather` | `intent == "action"` | `plan_action`锛涘惁鍒?`answer_with_citations` |
| `route_after_plan` | `state["gate"]` | `GATE_TO_NODE` 鎶?4 涓?gate 鏄犲皠鎴愯妭鐐瑰悕锛沗outcome` 鍙綋"娌″姙鎴?鐨勫垽鎹紝涓嶅綋璺敱鍊?|
| `route_after_confirm` | 椹冲洖 / 閲嶇畻鍚庣殑 `gate` | 椹冲洖 鈫?`compose_reply`锛涘崌绾?鈫?`approve_action`锛涘惁鍒?`execute_action` |
| `route_after_human` | `outcome` | 琚嫆 鈫?`compose_reply`锛涘惁鍒?鈫?`execute_action`锛堟病鏉冮檺鐨勪汉涓嶄細璧板埌杩欓噷锛岃妭鐐瑰唴浼氱户缁寕鍦ㄥ悓涓€涓?interrupt 涓婏級 |

**涓変釜闂搁棬鐨勫垎宸?*锛堥潰璇曞繀闂紝涔熸槸杩欎釜椤圭洰鏈€閲嶈鐨勮璁★級锛?
| 闂搁棬 | 璋佸湪璇磋瘽 | 瑙﹀彂鏉′欢 | 鐢ㄦ埛鐪嬪埌 |
|---|---|---|---|
| `ask_missing_info` | AI 闂€佸憳宸ョ瓟 | 鍙傛暟涓嶅叏锛堢己鍗曞彿/鏍囬/姝ｆ枃锛?| 涓€鍙ュ弽闂?|
| `confirm_action` | 鎻愬崟浜烘湰浜?| 鍙挙閿€鍐欙紙寤哄崟/鏀瑰崟/鍏冲崟锛?| 纭鍗★紝瀛楁鍙敼锛?*鏀瑰嚭涓嶅彲閫嗗弬鏁板氨閲嶇畻椋庨櫓骞跺崌绾у埌瀹℃壒** |
| `approve_action` | 鏈夋潈闄愮殑浜?| 涓嶅彲閫嗘垨鍏ㄥ憳鍙锛堝叧鍗?閫氱煡銆佸彂甯冪煡璇嗭級 | 瀹℃壒闃熷垪锛堝弬鏁?寮曠敤+鍘熸枃锛夛紱**鍙戣捣鈮犳壒鍑?*锛氳皝閮借兘鍙戣捣锛屽彧鏈?approver 鍦?resume 閭ｅ埢鑳界偣閫氳繃 |

鍘熷垯锛?*瀹＄殑鏄姩浣滐紝涓嶆槸鍥炵瓟**锛涘璇濋噷缁濅笉鎿呰嚜鎵ц锛屾嬁涓嶅噯灏卞厛绛斿啀闂€?鍐嶈ˉ涓夊彞锛堣繖涓夊彞鏄繖涓」鐩渶鍊奸挶鐨勮璁★級锛?*鍙戣捣鏉冨拰瀹℃壒鏉冨垎寮€**锛堝憳宸ヨ兘鎻愪氦鐢宠锛屼絾涓嶈兘鑷繁鎵癸級锛?*纭鏃舵敼鍙傛暟瑕侀噸绠楅闄?*锛堟妸"鍏冲崟"鏀规垚"鍏冲崟骞堕€氱煡"灏卞崌绾э級锛?*execute 鍐嶅厹搴曞鏍镐竴娆?*锛坄approval.approver` 涓虹┖灏辨嫆缁濇墽琛岋紝闃叉浠ュ悗鏀硅矾鐢辩粫杩囬椄闂級銆?
### 4.4 State 涓?Context锛堢槮韬悗鐨勭湡瀹炲瓧娈碉級

`UserContext`锛堟瘡娆?invoke 鍙锛屼笉杩?checkpoint锛夛細

```python
@dataclass(frozen=True)
class UserContext:
    user_id: str
    tenant_id: str
    roles: tuple[str, ...] = ("employee",)   # employee / approver / kb_owner
    display_name: str = "鍚屼簨"
```

`TicketState`锛堝浘鍐呭彲鍙橈紝宸插幓鎺?鍙啓涓嶈"鐨勫瓧娈碉級锛?
| 鍒嗙粍 | 瀛楁 | 璋佸啓 | 璋佽 |
|---|---|---|---|
| 韬唤涓庤緭鍏?| `tenant_id` `user_id` `query` | 鍏ュ彛 | 鍚勮妭鐐?|
| 鐞嗚В | `intent` `action` `classification` | `classify_request` | 璺敱 / `gather_evidence` / `plan_action` |
| 椋庨櫓涓庨椄闂?| `risk` `gate` | `plan_action`锛堟寜 `RISK_BY_OP` + `compute_risk` 閲嶇畻锛涚‘璁ゅ崱鏀瑰弬鏁板悗鍐嶇畻涓€娆★級 | 璺敱 / 涓夐椄闂?/ `execute_action` 鍏滃簳 |
| 璇佹嵁 | `policy_evidence` `facts` | `gather_evidence` | `answer` / `plan_action` / 纭鍗?|
| 鍔ㄤ綔 | `action`锛坄op`/`args`/`missing`/`sources`锛屽弬鏁板敮涓€鐪熺浉锛塦gate` | `plan_action`锛涚‘璁ゅ崱鐩存帴鏀?`action.args` | 涓夐椄闂?/ `execute_action` |
| 瀹℃壒 | `approval`锛堣皝鎵圭殑锛?| 涓夐椄闂?| `execute_action` / `compose_reply` |
| 缁撴灉 | `result` `via` `reply` `outcome`锛坉enied / rejected / failed锛屾甯镐负绌猴級 | `execute_action` / 鍥炲鑺傜偣 | CLI / 涓嬩竴姝?FastAPI |

### 4.5 涔濅釜 MCP 宸ュ叿锛? 涓?FastMCP server锛?
| server | 宸ュ叿 | 璇诲啓 | 闂搁棬 |
|---|---|---|---|
| ticket | `query_ticket` / `list_tickets` | 璇?| 鈥?|
| ticket | `create_ticket` / `update_ticket` / `close_ticket(notify_reporter)` | 鍐櫬峰彲鎾ら攢 | 纭 |
| kb | `search_kb` | 璇?| 鈥?|
| kb | `publish_kb_article(status)` | 鍐櫬蜂笉鍙€嗭紙`published`锛?| 瀹℃壒 |
| ticket | `save_approval` / `list_approvals` | 娌荤悊锛堝鎵圭暀鐥?/ 瀹℃壒涓績锛?| 鈥?|

- 瑁呴厤锛歚MultiServerMCPClient({"ticket": {...}, "kb": {...}})`锛宻tdio 璧风嫭绔嬭繘绋嬶紱娌欑绂佹瀛愯繘绋嬫椂鑷姩闄嶇骇杩涚▼鍐呰皟鐢紙鍗忚涓€鑷淬€佸疄鐜板悓婧愶級銆?- 椋庨櫓鍒嗙骇鍦?`plan_action.compute_risk`锛歚close_ticket(notify_reporter=True)` 鍗囩骇涓轰笉鍙€嗭紝`publish_kb_article(status="published")` 涓嶅彲閫嗭紙鍙戝竷鐭ヨ瘑鍙湁 published 涓€绉嶏級銆?
**宸ュ叿灞傞壌鏉冿紙鏈」鐩嫇灞曪紝浠ｇ爜鍦?backend/app/mcp/servers/guard.py锛?*

| 瑙掕壊 | 鑳借 | 鑳藉啓/鍏?| 鑳藉彂甯冪煡璇?|
|---|---|---|---|
| employee | 鍙湁鑷繁鎻愬崟 | 鍙湁鑷繁鎻愬崟 | 鍚?|
| approver | 鏈鎴峰叏閮?| 鏈鎴峰叏閮?| 鍚?|
| kb_owner | 鑷繁鎻愬崟 | 鑷繁鎻愬崟 | 鏄?|

- 姣忎釜宸ュ叿绗竴涓弬鏁版槸 `actor = {user_id, tenant_id, roles}`锛岀敱鑺傜偣浠?**Runtime Context** 鏋勯€狅紙`state.actor_of(runtime)`锛夛紝**缁濅笉浠庢ā鍨嬭緭鍑哄彇**锛?- server 鐢ㄥ畠瑕嗙洊 `tenant_id` / `reporter`锛屾ā鍨嬪～鐨勫€间竴寰嬩笉鐢熸晥锛涜法绉熸埛鐩存帴 `forbidden`锛?- 娌′紶 actor 鈫?`unauthorized`锛涘憳宸ユ煡/鍏冲埆浜虹殑鍗?鈫?`forbidden`锛堝嵆浣?Agent 琚粫杩囦篃鎷﹀緱浣忥級锛?- 寤哄崟鍘婚噸涔熸尓鍒?server锛氬悓绉熸埛 + 鍚屾彁鍗曚汉 + 鍚屾爣棰樼殑鏈叧闂崟鐩存帴鍥炲師鍗曪紙`deduplicated: true`锛夈€?
### 4.6 妫€绱㈤摼璺紙Milvus 瀹樻柟娣峰悎妫€绱?+ Cross-Encoder 绮炬帓浜岀骇婕忔枟锛?
1. `rag/embedding.py`锛歚OpenAIEmbeddings(model=text-embedding-v4, dimensions=1024)`锛圖ashScope 鍏煎绔偣锛夈€?2. `rag/vector_store.py`锛歝ollection `smartdesk_kb`锛屽瓧娈?`pk / doc_id / tenant_id / title / h1 / h2 / content / doc_status / dense / sparse`锛沗content` 寮€涓枃 analyzer + 鍐呯疆 `Function(FunctionType.BM25)`锛岀█鐤忓悜閲忕敱 Milvus 鐢熸垚銆?3. 绗竴闃舵绮楁帓锛歚client.hybrid_search([AnnSearchRequest(dense, COSINE), AnnSearchRequest(sparse, BM25)], ranker=RRFRanker(k=60), limit=10)`鈥斺€旇瀺鍚堝湪鏈嶅姟绔紝蹇€熺瓫鍑?Top-10 鍊欓€夈€?4. 绗簩闃舵绮炬帓锛歚rag/reranker.py` 澶嶇敤 `DASHSCOPE_API_KEY` 涓?`httpx` 闀胯繛鎺ユ睜璋冪敤 `gte-rerank-v2` 鍋?query-chunk 浜ゅ弶鎵撳垎锛屽苟涓?RRF 鍒嗗仛 Min-Max 褰掍竴鍖栬瀺鍚堬紙`alpha=0.5`锛夊彇鏈€缁?Top-3锛涜秴鏃舵垨寮傚父鑷姩闄嶇骇鍥?RRF 绮楁帓缁撴灉銆?5. 杩囨护锛歚tenant_id == "..." and doc_status == "published"`锛堝绉熸埛 + 鍙鎬т笉鍙橀噺锛夈€?6. `knowledge.py` 鏄敮涓€闂ㄩ潰锛氳繛涓嶄笂鐩存帴鎶?`MilvusUnavailable`锛屼笉鍋氬亣鍚戦噺鍏滃簳銆?
### 4.7 鐩綍缁撴瀯锛堢幇鐘讹級

```
backend/app/agents/
  state.py  graph.py  knowledge.py  llm.py  settings.py  checkpoint.py
  nodes/    classify / gather_evidence / answer / plan_action /
            clarify / confirm / approve / execute / respond / human_gate
  prompts/  service_desk.py
  rag/      embedding.py  vector_store.py  reranker.py锛堢簿鎺掞級  pdf_parser.py锛圡inerU锛? splitter.py锛堢粨鏋勫垏鍒嗭級
  tools/    mcp_client.py  ticket_tools.py  kb_tools.py
backend/app/mcp/servers/  ticket_server.py  kb_server.py  guard.py锛堝伐鍏峰眰閴存潈锛?scripts/    run_graph.py  trace_run.py  env_status.py  eval_rag.py  ingest_docs.py
            gen_kb_pdfs.py  reset_demo.py
deploy/     docker-compose.yml锛坧ostgres / milvus / etcd / attu锛? init/01_init.sql
docs/       AGENT-CODE-REFERENCE.md  STUDY-GUIDE.md  architecture/main-graph.mmd
            eval/golden_set.jsonl锛?1 鏉★級  eval/report.md锛堣瘎娴嬫姤鍛婏級
            kb/锛? 浠藉埗搴︽枃妗ｇ殑 src / pdf / md / chunks.jsonl锛?```

### 4.8 宸茬粡鍋氬畬 vs 杩樻病鍋?
**褰撳墠浠ｇ爜瑙勬ā**锛歚backend/` 绾?4200 琛?/ 36 涓?py锛坅gents 鑺傜偣 1278銆乺ag 825銆乵cp 612銆乼ools 371銆乤pi 525銆佹牴 617锛夛紝`scripts/` 1531 琛岋紝`frontend/src` 1529 琛?/ 13 涓枃浠讹紱鍒犻櫎/鍚堝苟鍚庢€昏鏁版瘮閲嶆瀯鍓嶅皯绾?20%銆?
**宸插畬鎴愶紙鏈夌湡瀹炶繍琛岃褰曪級**锛氫節鑺傜偣涓诲浘銆佸洓鏉¤矾锛堢煡璇?/ 纭 / 瀹℃壒 / 婢勬竻锛夈€?*9 涓?MCP 宸ュ叿锛堝伐鍗?5 + 鐭ヨ瘑 2 + 娌荤悊 2锛?*銆?*宸ュ叿灞傞壌鏉冿紙server 渚ф寜瑙掕壊鍒ゆ潈 + 鏈嶅姟绔幓閲嶏級**銆?*瀹℃壒钀借〃锛坅pprovals 涓€寮犺〃銆佸惈 thread_id 鍏ㄩ摼璺疮閫?Web 瀹℃壒涓績锛?*銆?*瀹℃壒璇箟淇锛堝彂璧封墵鎵瑰噯锛氬憳宸ュ彲鎻愪氦锛屼富绠¤法杩涚▼ resume 鎵嶇敓鏁堬紱纭鏀瑰嚭涓嶅彲閫嗗弬鏁颁細閲嶇畻椋庨櫓骞跺崌绾э紱execute 鍏滃簳澶嶆牳 approval.approver锛?*銆?*鐪熷疄鐭ヨ瘑搴撳叆搴擄紙7 浠藉埗搴︽枃妗?鈫?PDF 鈫?MinerU 瀹樻柟 SDK 瑙ｆ瀽 鈫?缁撴瀯鎰熺煡鍒囧垎 97 chunk 鈫?Milvus dense+BM25锛?*銆?*浜岀骇妫€绱㈡紡鏂楋紙Milvus RRF Top-10 绮楁帓 鈫?DashScope `gte-rerank-v2` Cross-Encoder 绮炬帓铻嶅悎 Top-3锛屽惈浼橀泤闄嶇骇锛?*銆丳G checkpoint锛堣法杩涚▼鎭㈠锛夈€丆LI 涓冨瓙鍛戒护 + `reset_demo`銆侀€愯妭鐐硅窡璇诲伐鍏枫€?*51 鏉?golden set 娑堣瀺瀵规瘮璇勬祴锛圧RF vs RRF+绮炬帓 / 寮曠敤 / 寤惰繜锛?*銆?*FastAPI + SSE + Vue3 鎺у埗鍙颁笁椤碉紙浼氳瘽宸ヤ綔鍙?+ 鍙闃呭崟鎹?+ 杩愯鏃堕潰鏉?/ 瀹℃壒鐪嬫澘+鎶藉眽 / 宸ュ崟鐪嬫澘锛?*銆?
**寰呭仛锛堣繘闃舵墿灞曪級**锛氬彲瑙傛祴锛圠angSmith trace + 鑺傜偣鑰楁椂澶х洏锛夈€佺煡璇嗗簱鎵╁埌 50鈥?00 绡囩湡瀹炴枃妗?+ Query Rewrite銆丣WT 鎹㈡帀璇锋眰澶磋韩浠姐€?
### 4.9 绠€鍘嗛噷瑕佺殑鏁板瓧锛堥兘鏄湰鏈哄疄娴嬶級

璺戞硶锛歚python -m scripts.eval_rag --compare --answers 20`锛?1 鏉?golden set锛? 浠藉埗搴︽枃妗ｃ€?7 涓?chunk锛屾爣娉ㄥ埌銆屾枃妗?+ 灏忚妭銆嶏級锛?
| 鎸囨爣 | 绾?RRF (Top-3) | **RRF Top-10 + `gte-rerank-v2` 绮炬帓** | 閲囬泦鏂瑰紡 |
|---|---|---|---|
| 妫€绱?Recall@1 | 82.35% | **86.27%** (+3.92pp) | 鏈熸湜灏忚妭鎺掔涓€ |
| 妫€绱?Recall@3 | 96.08% | **98.04%** (+1.96pp锛?0/51) | 鏈熸湜灏忚妭杩涘墠 3 |
| MRR@3 | 0.8922 | **0.9150** (+0.0228) | 鎺掑悕鍊掓暟鐨勫潎鍊?|
| 妫€绱㈠欢杩?| 骞冲潎 235 ms / P95 330 ms | 骞冲潎 **382 ms** / P95 **486 ms** | 鍗曟妫€绱㈠叏閾捐矾锛堝凡棰勭儹锛?|
| 寮曠敤鍑嗙‘鐜?| 鈥?| **100%**锛?0 鏉＄鍒扮锛?| 鍥炵瓟寮曠敤鐨勮祫鏂欓噷鍚湡鏈涘皬鑺?|
| 寮曠敤鏍囨敞鐜?| 鈥?| **100%** | 鍥炵瓟姝ｆ枃甯?[1] 鏍囨敞 |
| 绔埌绔欢杩?| 鈥?| 骞冲潎 **3.37 s** / P95 **4.22 s** | 鍒嗙被 + 妫€绱㈢簿鎺?+ 鐢熸垚 |
| 鐭ヨ瘑搴撹妯?| 鈥?| 7 浠芥枃妗?/ 42 绔?/ **97 chunk** | docs/kb/chunks.jsonl |
| 瀹℃壒瑕嗙洊 | 鈥?| 涓氬姟 7 涓伐鍏烽噷 2 涓己鍒跺鎵?| 鍏冲崟+閫氱煡銆佸彂甯冪煡璇?|
| 娌荤悊鐣欑棔 | 鈥?| 瀹℃壒 4 鎬侊紙pending / approved / edited / rejected锛?| approvals 涓€寮犺〃锛學eb/CLI 鍙煡 |
| 鏉冮檺鐭╅樀 | 鈥?| 3 瑙掕壊 脳 3 绫绘搷浣滐紝瓒婃潈鍏ㄩ儴琚嫆 | 鏌?鏀?鍏充粬浜哄崟銆佽法绉熸埛銆佹棤 actor |

> 绠€鍘嗗彲鐩存帴鎶勶細鍩轰簬 Milvus 鍙岃矾鍙洖锛圖ense + 鍐呯疆涓枃 BM25 + RRF 绮楁帓 Top-10锛変笌 `gte-rerank-v2` Cross-Encoder 绮炬帓鏋勫缓浜岀骇妫€绱㈡紡鏂楋紱鍦?51 鏉＄湡瀹為棶鍙ヨ瘎娴嬮泦锛?7 chunk锛変笂鍋氭秷铻嶉獙璇侊紝Recall@1 浠?82.35% 鎻愬崌鑷?**86.27%**銆丷ecall@3 浠?96.08% 鎻愬崌鑷?**98.04%**銆丮RR@3 鎻愬崌鑷?**0.9150**锛?0 鏉＄鍒扮鐢ㄤ緥寮曠敤鍑嗙‘鐜?**100%**銆?
### 4.10 涓変釜"闈㈣瘯鍙"鐨勫彇鑸?
1. **涓轰粈涔堜笉鐢?`create_agent` 涓€鎶婃**锛氶渶瑕佷笁涓笉鍚岀殑"浜?鍦ㄤ笉鍚岀偣浠嬪叆锛宍create_agent` 鍙湁宸ュ叿绾у鎵归挬瀛愶紝鍋氫笉鍑?纭鍗?+ 瀹℃壒闃熷垪"銆?2. **涓轰粈涔堝垎鏀啓鍦?graph.py 鑰屼笉鏄妭鐐归噷 `Command(goto)`**锛氬喅绛栭泦涓湪涓€涓枃浠躲€佽兘琚敾鍑烘潵銆佽兘琚崟鐙祴锛涜妭鐐瑰彧绠楄嚜宸遍偅娈点€?3. **涓轰粈涔堟绱㈠湪 Milvus 鑰屼笉鍦?Python**锛歞ense + BM25 + RRF 閮芥槸鏈嶅姟绔兘鍔涳紱鎵嬪啓 RRF 鏃㈡參鍙堝拰绱㈠紩 metric 瀹规槗涓嶄竴鑷淬€?4. **涓轰粈涔?SSE 涓嶇敤 WebSocket**锛氳繖鏄崟鍚戞祦锛堟湇鍔＄鎶?token / 鑺傜偣杩涘害 / interrupt 鎺ㄧ粰鍓嶇锛屽墠绔彧鍦ㄧ敤鎴风偣鎸夐挳鏃跺彂 REST锛夛紱SSE 璧版櫘閫?HTTP锛屾柇绾块噸杩炲拰 `curl` 灏辫兘楠岋紝WebSocket 瑕佸涓€灞傝繛鎺ョ鐞嗭紝鏀剁泭鍙湁涓€涓?鍙屽悜"鎴戜滑娌＄敤鍒般€傜湡闇€瑕佹墦鏂敓鎴愭椂锛岀敤 `X-Accel-Buffering: no` + 鍓嶇 abort 璇锋眰鍗冲彲銆?## 5. 钀藉湴璺嚎锛堝凡瀹屾垚 / 鍓╀綑锛?
| 闃舵 | 鍐呭 | 鐘舵€?|
|---|---|---|
| 1 | 涓诲浘璺戦€氾細涔濊妭鐐?+ 涓夐椄闂?+ `interrupt` / `Command(resume=)` | 鉁?瀹屾垚 |
| 2 | Milvus 鐭ヨ瘑搴擄細娣峰悎妫€绱?+ 寮曠敤 + 澶氱鎴疯繃婊?| 鉁?瀹屾垚 |
| 3 | MCP 宸ュ叿鍖栵細2 server / 10 宸ュ叿 + 椋庨櫓鍒嗙骇 + 骞傜瓑鍘婚噸 | 鉁?瀹屾垚 |
| 4 | 鎸佷箙鍖栧垏鎹細`SqliteSaver` 鈫?`PostgresSaver`锛堣法杩涚▼鎭㈠锛?| 鉁?瀹屾垚 |
| 5 | 浠ｇ爜浣撴锛氬懡鍚嶇粺涓€銆佸垹鍐椾綑銆佽矾鐢遍泦涓€丼tate 鐦﹁韩 | 鉁?瀹屾垚 |
| 6 | FastAPI + SSE锛氭妸 CLI 鎹㈡垚 HTTP 鎺ュ彛锛屽墠绔兘鎺?| 鉁?瀹屾垚 |
| 7 | Vue3 涓夐〉锛氫細璇濆伐浣滃彴锛圫SE + 鍙闃呴椄闂ㄥ崟鎹?+ 杩愯鏃堕潰鏉匡級/ 瀹℃壒鐪嬫澘 / 宸ュ崟鐪嬫澘 | 鉁?瀹屾垚 |
| 8 | 璇勬祴涓庡寘瑁咃細golden set銆丷RF vs 绮炬帓娑堣瀺瀵规瘮琛ㄣ€丷EADME銆佽瑙ｅ崱 | 鉁?瀹屾垚 |

姣忛樁娈甸獙鏀舵爣鍑嗭細鑳借窇璧锋潵 + 鑳芥埅鍥?+ 鑳借娓?涓轰粈涔堣繖涔堝仛"銆?## 6. 绠€鍘嗗啓浣滀笌闈㈣瘯鍑嗗

### 6.1 椤圭洰鎻忚堪妯℃澘锛? 鏉?bullet锛屾暟瀛楀凡鎸夊疄娴嬪～濂斤級

> **SmartDesk-Agent锝滀紒涓氬唴閮ㄦ湇鍔″彴 Agent 骞冲彴**锛堜釜浜洪」鐩?/ 2026.xx鈥?026.xx锛?> 鎶€鏈爤锛歅ython 3.12 路 LangGraph 路 LangChain 1.x 路 MCP锛團astMCP锛?路 Milvus 路 PostgreSQL 路 FastAPI + SSE

- 鍩轰簬 **LangGraph 涔濊妭鐐逛富鍥?*瀹炵幇"鎻愰棶 鈫?鍙栬瘉鎹?鈫?鍥炵瓟/鍔ㄦ墜"瀹屾暣閾捐矾锛岀敤鏉′欢杈规妸**婢勬竻銆佺‘璁ゃ€佸鎵?*涓夌被浜哄伐浠嬪叆鎷嗘垚涓変釜鐙珛闂搁棬锛屽仛鍒?涓嶅彲閫嗗姩浣?100% 闇€鎺堟潈"銆?- 鐢?**PostgresSaver + thread_id** 璁╁鎵瑰彲璺ㄨ繘绋嬫仮澶嶏細杩涚▼閫€鍑哄悗鏂拌繘绋?`resume` 缁х画璺戯紝瀹℃壒绛夊緟涓嶄緷璧栧唴瀛橈紱杩炰笉涓?PG 鑷姩闄嶇骇 SQLite銆?- 鏋勫缓 **Milvus 娣峰悎鍙洖 + Cross-Encoder 绮炬帓浜岀骇妫€绱㈡紡鏂?*锛氱涓€闃舵鐢ㄧ瀵嗗悜閲忥紙1024 缁?COSINE锛? 鏈嶅姟绔唴缃腑鏂?BM25 缁?`RRFRanker(k=60)` 绮楁帓 Top-10锛岀浜岄樁娈佃皟 `gte-rerank-v2` 浜ゅ弶鎵撳垎骞朵笌 RRF 褰掍竴鍖栬瀺鍚堝彇 Top-3锛堣秴鏃跺紓甯歌嚜鍔ㄩ檷绾у洖 RRF锛夛紱绛旀寮哄埗甯?`[1][2]` 寮曠敤锛堢簿纭埌"绗?X 绔?路 X.Y 鑺?锛夛紝妫€绱笉鍒版椂鏄庣‘鍛婄煡骞剁粰鍑轰笅涓€姝ャ€?- 鐭ヨ瘑搴撴槸**鐪熸枃妗ｆ祦姘寸嚎**锛? 浠戒紒涓氬埗搴︽枃妗?鈫?PDF 鈫?**MinerU 瀹樻柟 SDK 瑙ｆ瀽鎴?Markdown** 鈫?`MarkdownHeaderTextSplitter` 缁撴瀯鎰熺煡鍒囧垎锛堝師鏂?97 chunk锛岄潰鍖呭睉鍥炲～鍒版瘡涓?chunk锛夆啋 甯?`source_file / h2 / h3 / chunk_index` 鐨?Milvus 闆嗗悎锛屽箓绛?upsert 鍙噸澶嶅叆搴撱€?- 鎶婂缓鍗?鏀瑰崟/鍏冲崟/鍙戝竷鐭ヨ瘑灏佽鎴?**2 涓?FastMCP server / 9 涓伐鍏?*锛堝伐鍗?5 + 鐭ヨ瘑 2 + 娌荤悊 2锛夛紝鐢?`MultiServerMCPClient` 瑁呴厤锛?*鏉冮檺鍒ゅ畾鏀惧湪 server 渚?*锛? 瑙掕壊 脳 3 绫绘搷浣滐紝瓒婃潈璇锋眰涓€寰?`forbidden`锛夛紝鍐欐搷浣滄寜椋庨櫓鍒嗙骇璧扮‘璁ゆ垨瀹℃壒锛屽苟鐢?*鏈嶅姟绔幓閲?*锛堝悓绉熸埛 + 鍚屾彁鍗曚汉 + 鍚屾爣棰樼殑鏈叧闂崟鐩存帴鍥炲師鍗曪級閬垮厤閲嶅寤哄崟銆?- 瀹℃壒**钀芥湇鍔＄涓€寮犺〃**锛坄approvals` 4 鎬佺姸鎬佹満锛夛紝CLI `approvals` 瀛愬懡浠ゅ嵆"瀹℃壒涓績"鐨勬暟鎹簮锛沗save_approval` 骞傜瓑锛宍interrupt` 鎭㈠閲嶆斁涓嶄細閲嶅鎻掑崟銆?*鍙戣捣鏉冨拰瀹℃壒鏉冨垎寮€**锛氬憳宸ュ彲浠ュ彂璧蜂笉鍙€嗗姩浣滆繘鍏?pending 闃熷垪锛屽彧鏈?approver 鐢ㄥ悓涓€鏉?`thread_id` 鏉?`resume` 鎵嶇敓鏁堬紙璺ㄨ繘绋嬫紨绀哄鎵癸級锛涚‘璁ゅ崱閲屾敼鍑轰笉鍙€嗗弬鏁颁細閲嶇畻椋庨櫓骞惰ˉ涓€閬撳鎵癸紱`execute_action` 鏈€鍚庡啀澶嶆牳 `approval.approver`锛涙病鏉冮檺鐨勪汉鐐归€氳繃**鐩存帴鍥炰竴鍙ヨ瘽缁撴潫**锛坄outcome=denied`锛夛紝涓嶆浛浠栧仛鍐冲畾锛涜秺鏉冩搷浣滐紙鍔ㄥ埆浜虹殑鍗?娌?kb_owner 鍙戠煡璇嗭級鍦?`plan_action` 灏辨寜 server 杩斿洖鐨?`can_write` 鐩存帴鎷掔粷锛堝悓鏍?`outcome=denied`锛夛紝涓嶅脊鍗′笉鎺掗槦銆?- **FastAPI + SSE 鎺ュ叆**锛歚POST /api/v1/chat/stream` 鎶婂浘浜嬩欢瀹炴椂鎺ㄧ粰鍓嶇锛坄meta 鈫?node 鈫?token 鈫?interrupt 鈫?done`锛宼oken 鍙浆鍙?`answer_with_citations` 鐨勫閲忥級锛涘仠涓嬫椂鍓嶇鎷垮埌 `interrupt` 杞借嵎锛堢瓑浜庝竴寮犵‘璁?瀹℃壒鍗＄墖锛夛紝鐐规寜閽蛋 `POST /runs/{id}/resume`锛?*鍚屼竴鏉?thread_id 鍙崲韬唤 resume**锛堝憳宸ュ彂璧枫€佷富绠¤法杩涚▼鎵瑰噯灏辨槸杩欎箞婕旂殑锛夛紱HTTP 灞傚彧鍋?瑙ｆ瀽璇锋眰 鈫?缁?`UserContext` 鈫?璋?`get_graph()`"锛屾潈闄愪粛鍦?MCP server锛?04/403/409 涓夌閿欒鍒嗗紑銆?- 鑷缓 **51 鏉?golden set**锛堢湡瀹為棶鍙ュ 97 chunk锛夊仛娑堣瀺璇勬祴锛氬紩鍏ョ簿鎺掑悗妫€绱?**Recall@1 浠?82.35% 鎻愬崌鑷?86.27%锛?3.92pp锛夈€丷ecall@3 浠?96.08% 鎻愬崌鑷?98.04%锛?1.96pp锛夈€丮RR@3 浠?0.8922 鎻愬崌鑷?0.9150**锛?0 鏉＄鍒扮鐢ㄤ緥**寮曠敤鍑嗙‘鐜?100%**锛屾绱?P95 486 ms銆佺鍒扮骞冲潎 3.37 s / P95 4.22 s銆?
锛堜互涓婃暟瀛楀叏閮ㄦ潵鑷?`python -m scripts.eval_rag --compare --answers 20` 鐨勭湡瀹炶緭鍑猴紝鎶ュ憡鍦?`docs/eval/report.md`锛涙崲鏈哄櫒鎴栨崲妯″瀷鍚庨噸璺戝啀鏀规暟瀛楋紝**娌℃祴鐨勪笉瑕佸啓**銆傦級
### 6.2 宸啓娉?vs 濂藉啓娉?
| 鉂?宸?| 鉁?濂?| 涓轰粈涔?|
|---|---|---|
| 浣跨敤 LangChain 鍜?LangGraph 寮€鍙戜簡涓€涓櫤鑳藉鏈嶇郴缁燂紝瀹炵幇浜嗙煡璇嗗簱闂瓟鍔熻兘銆?| 鍩轰簬 LangGraph 鏋勫缓宸ュ崟澶勭悊涓诲浘锛岀敤 `interrupt` 瀹炵幇浜哄伐瀹℃壒銆乣PostgresSaver` 鎸佷箙鍖栵紝鏈嶅姟閲嶅惎鍚庡鎵逛粛鍙仮澶嶃€?| 鏈夋鏋剁粏鑺傘€佹湁鏈哄埗銆佹湁鍙獙璇佺殑鏁堟灉 |
| 浣跨敤 Milvus 鍋氬悜閲忔绱紝鏁堟灉寰堝ソ銆?| Milvus 绋犲瘑+BM25 娣峰悎妫€绱紙RRF k=60锛? gte-rerank-v2 绮炬帓锛孯ecall@5 浠?0.61 鈫?0.87銆?| 鏈夋柟妗堝姣斻€佹湁鎸囨爣 |
| 瀹炵幇浜嗗 Agent 鍗忎綔銆?| 鐢?Send API 鎸変骇鍝佺嚎骞惰 N 涓垎鏋?worker锛屾棩鎶ョ敓鎴愪粠 3 鍒嗛挓闄嶈嚦 40 绉掋€?| 鏈夊叿浣?API銆佹湁瀵规瘮鏁板瓧 |
| 鐔熸倝 FastAPI 鍜?Vue銆?| FastAPI + SSE 鎶?Agent 浜嬩欢娴佸紡鎺ㄧ粰鍓嶇锛坱oken 閫愬瓧銆乮nterrupt 浜嬩欢甯﹀鎵瑰崱鐗囷級锛宺esume 璧板悓涓€ thread锛涘鎵归€氳繃鍒版墽琛屽畬鎴愬疄娴?380 ms銆?| 鎶€鑳藉啓鎴?鍋氬埌浠€涔堢▼搴? |

### 6.3 鎶€鏈爤琛岀殑鍐欐硶

鍒嗕笁妗ｅ啓锛屽埆涓€琛屽婊★細
- **鐔熺粌**锛歅ython銆丗astAPI銆丩angChain銆丩angGraph銆丷AG銆丮ilvus銆丼QL
- **鎺屾彙**锛歁CP銆乂ue3銆丳ostgreSQL銆丏ocker銆丼SE銆丷edis
- **浜嗚В**锛歀angSmith銆乿LLM銆並8s銆丆lickHouse

### 6.4 楂橀闈㈣瘯 17 闂紙鎸変綘椤圭洰浼氳拷闂殑椤哄簭锛?
**A. LangGraph / 鐘舵€?*
1. `create_agent` 搴曞眰鍋氫簡浠€涔堬紵鍜屾墜鍐?`StateGraph` 鏈変粈涔堝尯鍒紵锛堢瓟锛歭lm 鑺傜偣 + tools 鑺傜偣 + 鏉′欢杈?+ compile锛涙墜鍐欐墠鑳藉仛澶氳妭鐐逛笟鍔＄紪鎺掍笌 interrupt 瀹℃壒锛?2. `AgentState` 鏄粈涔堬紵reducer锛坄Annotated[list, add_messages]` / `operator.add`锛夎В鍐充粈涔堥棶棰橈紵涓嶅啓 reducer 浼氭€庢牱锛燂紙榛樿瑕嗙洊锛屽苟琛屽垎鏀細涓㈡暟鎹級
3. Context / State / Store 涓夎€呯殑鍖哄埆鍜岀敓鍛藉懆鏈燂紵锛堝崟娆¤皟鐢ㄥ彧璇?/ 鍗?thread 鍙彉 / 璺?thread 鎸佷箙锛?4. 涓轰粈涔?`interrupt` 蹇呴』閰?checkpointer锛熸仮澶嶆椂鍙戠敓浜嗕粈涔堬紵锛堟殏鍋滅偣鍐欏叆 checkpoint锛宍Command(resume=...)` 浠庤鐐圭画璺戯級
5. `HumanInTheLoopMiddleware` 鍜屾墜鍐?`interrupt` 鎬庝箞閫夛紵锛堝伐鍏风骇鍗遍櫓鍔ㄤ綔 鈫?Middleware锛涢渶瑕佸睍绀轰笟鍔′笂涓嬫枃鐨勫瀛楁瀹℃壒 鈫?鎵嬪啓锛?6. `Command(goto=...)` 鍜?`add_conditional_edges` 鎬庝箞閫夛紵锛堝喅绛栦笌鏇存柊鍚屾簮鏃剁敤 Command锛岀函鍒嗘敮鐢ㄦ潯浠惰竟锛?
**B. RAG / Milvus**
7. 绋犲瘑 vs 绋€鐤忓悇鎿呴暱浠€涔堬紵涓轰粈涔堣娣峰悎妫€绱紵涓枃鍒嗚瘝鎬庝箞閰嶏紵锛坄analyzer_params={"type":"chinese"}`锛?8. 涓轰粈涔堢敤 RRF 鑰屼笉鏄姞鏉冭瀺鍚堬紵k=60 鏄粈涔堬紵鍔犳潈鍓嶄负浠€涔堣褰掍竴鍖栵紵
9. 涓ら樁娈垫绱紙Bi-Encoder 鍒濈瓫 + Cross-Encoder 绮炬帓锛変负浠€涔堜究瀹滐紵`fetch_k` 鎬庝箞瀹氾紵
10. chunk 澶у皬 / overlap 鎬庝箞瀹氾紵`MarkdownHeaderTextSplitter` 鏈変粈涔堝ソ澶勶紵锛堜繚鐣欐爣棰樺眰绾у仛 metadata 杩囨护涓庢函婧愶級
11. 2-Step RAG 鍜?Agentic RAG 鎬庝箞鍙栬垗锛燂紙鍥哄畾闂瓟鐢?2-Step 鐪侀挶绋冲畾锛涘璺?闇€鍒ゆ柇鏄惁妫€绱㈢敤 Agentic锛?12. 鎬庝箞璇勬祴 RAG锛烺ecall@5 / MRR / 寮曠敤鍑嗙‘鐜囧垎鍒€庝箞绠楋紵golden set 鎬庝箞閫狅紵

**C. MCP / 澶?Agent / 宸ョ▼**
13. MCP 鏄粈涔堬紵Host/Client/Server 鍏崇郴锛焥tdio 涓?streamable_http 鍚勮嚜閫傜敤鍦烘櫙锛?14. 鎬庝箞淇濊瘉 MCP 宸ュ叿瀹夊叏锛燂紙绉熸埛鐧藉悕鍗曘€佸彧璇昏处鍙枫€丼QL 琛ㄧ櫧鍚嶅崟 + LIMIT銆佽秴鏃堕噸璇曘€佸璁℃棩蹇楋級
15. 浠€涔堟椂鍊欏€煎緱涓婂 Agent锛烻ubagents 涓?Handoffs 鐨勫尯鍒紵涓轰粈涔?浼樺厛鍗?Agent"锛?16. SSE 娴佸紡鎬庝箞瀹炵幇锛熸柇绾块噸杩炪€佸崐鎴伐鍏疯皟鐢ㄣ€佸墠绔浣曟覆鏌撳伐鍏风姸鎬侊紵
17. 鐢熶骇涓婃€庝箞鎺ф垚鏈笌寤惰繜锛燂紙妯″瀷璺敱/闄嶇骇銆佹憳瑕佷腑闂翠欢銆乪mbedding 缂撳瓨銆佸紓姝ュ寲銆佸苟琛?Send锛?
> 鍑嗗鏂瑰紡锛氭瘡棰樺啓鎴?30 绉掔増 + 2 鍒嗛挓鐗?锛? 鍒嗛挓鐗堝繀椤昏惤鍒颁綘椤圭洰閲岀殑鍏蜂綋鏂囦欢鍜屼唬鐮併€?
### 6.5 宀椾綅鍖归厤锛堟姇閫掓椂鎬庝箞瀵逛笂 JD锛?
| JD 鍏抽敭璇?| 浣犻」鐩噷鐨勫搴旇瘉鎹?|
|---|---|
| 鐔熸倝 LangChain / LangGraph | 涓诲浘 + 瀛愬浘 + Command 璺敱 + checkpointer |
| RAG / 鍚戦噺鏁版嵁搴?| Milvus 鍙岃矾娣峰悎妫€绱?+ 绮炬帓 + 璇勬祴鎶ュ憡 |
| Agent 宸ュ叿璋冪敤 / MCP | FastMCP 涓変釜 Server + 鍔ㄦ€佹寕杞?+ 瀹¤ |
| 鍚庣鏈嶅姟寮€鍙?| FastAPI 鍒嗗眰 + SSE + JWT/RBAC + 寮傛浠诲姟 |
| 宸ョ▼鍖?/ 閮ㄧ讲 | Docker Compose 涓€閿捣 + 鏃ュ織 |
| 鍓嶇锛堣嫢鏈夛級 | Vue3 瀹℃壒涓績 + 妫€绱㈣皟璇曞彴 |

---

## 7. 閬垮潙娓呭崟涓庡姞鍒嗛」

### 7.1 鍗佷釜鏈€甯歌鐨勫潙

| # | 鍧?| 鍚庢灉 | 姝ｇ‘鍋氭硶 |
|---|---|---|---|
| 1 | 鍙仛 demo锛氭棤閴存潈銆佹棤鍒嗛〉銆佹棤鏃ュ織 | 涓€鐪肩湅鍑烘槸缁冩墜椤圭洰 | 鍔?JWT + RBAC銆佺粺涓€寮傚父涓庢棩蹇椼€佸垎椤?|
| 2 | 鐭ヨ瘑搴撳彧鏈?5鈥?0 绡囨枃妗?| 妫€绱㈤毦搴﹀お浣庯紝浣撶幇涓嶅嚭鏂规浠峰€?| 鈮?00 绡囩湡瀹炴枃妗ｏ紝瑕嗙洊 FAQ/姝ラ/鎺掗殰 |
| 3 | 娌¤瘎娴嬶紝鎸囨爣闈犵紪 | 闈㈣瘯涓€闂粏鑺傚氨宕?| golden set + 璇勬祴鑴氭湰 + 鎶ュ憡钀界洏 |
| 4 | State 濉炰簡涓€鍫嗘棤鍏冲瓧娈?| 鍥鹃毦缁存姢锛宑heckpoint 鑶ㄨ儉 | 鍙斁涓嬫父鍐崇瓥闇€瑕佷笖涓嶅彲鎺ㄥ鐨勫瓧娈?|
| 5 | 鐢?`InMemorySaver` 鍗村啓"浼佷笟绾? | 閲嶅惎涓㈢姸鎬?| `PostgresSaver` / `SqliteSaver` |
| 6 | MCP 鍙皟鐢ㄥ埆浜虹幇鎴?Server | 浣撶幇涓嶅嚭"灏佽鍐呴儴绯荤粺" | 鑷繁鍐?2鈥? 涓?FastMCP Server |
| 7 | 杩囧害璁捐澶?Agent | 璋冭瘯鎴愭湰鐖嗙偢 | 鍏堝崟 Agent锛岀‘鏈夊苟琛?闅旂闇€姹傚啀鎷?|
| 8 | Prompt 鍏ㄧ‖缂栫爜鍦ㄤ唬鐮侀噷 | 鏃犳硶杩唬銆佹棤娉?A/B | `prompts/` 鐩綍 + 鐗堟湰瀛楁 |
| 9 | 宸ュ叿鏃犻噸璇曟棤瓒呮椂 | 澶栭儴绯荤粺涓€鎸傚叏閾捐矾鎸?| `RetryPolicy` + 瓒呮椂 + 闄嶇骇杩斿洖 `ToolMessage` |
| 10 | README 娌℃灦鏋勫浘/鎴浘/涓€閿儴缃?| 闈㈣瘯瀹樹笉浼氳窇浣犵殑浠ｇ爜 | 鏋舵瀯鍥?+ 3 寮犳埅鍥?+ `docker compose up` |

### 7.2 鍔犲垎椤癸紙鍋氬畬涓婇潰鍐嶅姞锛屾€т环姣旀帓搴忥級

1. **LangSmith trace 鎴浘**鏀捐繘 README锛氳瘉鏄庝綘鐪熺殑璋冭瘯杩囬摼璺€?2. **`docs/eval-report.md`**锛? 缁勬绱㈡柟妗堝姣旇〃锛屾瘮浠讳綍褰㈠璇嶉兘鏈夎鏈嶅姏銆?3. **涓€閿儴缃?*锛歚docker compose up -d` + `make demo`锛岄潰璇曞畼 10 鍒嗛挓鑳借窇璧锋潵銆?4. **3 鍒嗛挓婕旂ず瑙嗛 / GIF**锛氬鎵逛腑鏂?鈫?鎭㈠鐨勫畬鏁存紨绀猴紝鏈€鑳戒綋鐜?HITL銆?5. **鍥炲綊璇勬祴鎺?CI**锛圙itHub Actions锛夛細姣忔 PR 璺?golden set锛屾寚鏍囦笅闄嶅氨澶辫触銆?6. **鎶€鏈鐩樻枃绔?*锛氫緥濡傘€婁负浠€涔堟妸 InMemoryVectorStore 鎹㈡垚 Milvus銆嬨€奟RF 涓庡姞鏉冭瀺鍚堢殑瀹炴祴宸紓銆嬶紝鏀炬帢閲?鐭ヤ箮锛岀畝鍘嗛噷鏀鹃摼鎺ャ€?7. **鍙娴嬫€?*锛氳妭鐐硅€楁椂鐑姏鍥俱€乼oken 鎴愭湰鐪嬫澘銆?
### 7.3 浜や粯鍓嶆鏌ユ竻鍗曪紙閫愰」鎵撳嬀锛?
- [ ] `docker compose up -d` 鍦ㄦ柊鏈哄櫒鍙捣锛圥G / Redis / Milvus / attu / 鍚庣 / 鍓嶇锛?- [ ] README 鏈夛細涓€鍙ヨ瘽绠€浠嬨€佹灦鏋勫浘銆佸姛鑳芥埅鍥俱€佹寚鏍囪〃銆佸惎鍔ㄥ懡浠ゃ€佺洰褰曡鏄?- [ ] 婕旂ず璐﹀彿涓?demo 鏁版嵁涓€閿垵濮嬪寲
- [ ] 涓夋潯涓婚摼璺彲婕旂ず锛氱煡璇嗛棶绛斻€佸缓鍗曘€佽Е鍙戝鎵瑰苟鎭㈠
- [ ] `.env.example` 瀹屾暣锛屾棤鐪熷疄瀵嗛挜鍏ュ簱
- [ ] `docs/eval-report.md` 鏈夊墠鍚庡姣旀暟瀛?- [ ] 绠€鍘?4 鏉?bullet 鐨勬暟瀛楀叏閮ㄦ潵鑷湡瀹炶繍琛岃褰?- [ ] 闈㈣瘯 17 闂瘡棰樿兘璁?2 鍒嗛挓骞惰惤鍒颁唬鐮?
---

## 闄勫綍 A锛氱幆澧冧笌涓€閿捣姝?
### A.1 鐜瑕佹眰

| 缁勪欢 | 鐗堟湰 / 璇存槑 |
|---|---|
| Python | 3.12锛堟湰椤圭洰鐢?`.venv` 铏氭嫙鐜锛?|
| PostgreSQL | 16锛圖ocker锛宍deploy/docker-compose.yml`锛?|
| Milvus | 2.5+ / 2.6锛坉ense + 鍐呯疆 BM25锛?|
| attu | Milvus 鎺у埗鍙帮紝`http://localhost:8000` |
| Docker Desktop + WSL2 | 璧?PG / Milvus / etcd / attu 鍥涗釜瀹瑰櫒 |

### A.2 渚濊禆锛坄pyproject.toml` 鐜扮姸锛?
```toml
dependencies = [
  "langchain>=1.0", "langgraph>=1.0",
  "langgraph-checkpoint-sqlite>=2.0", "langgraph-checkpoint-postgres>=3.0",
  "langchain-openai>=1.0", "psycopg[binary]>=3.2", "pymilvus>=2.6",
  "python-dotenv>=1.0", "langchain-mcp-adapters>=0.3", "fastmcp>=2.0",
]
```

### A.3 `.env`锛堝彧闇€瑕佷袱涓?key锛屽叾浣欐湁榛樿鍊硷級

```ini
DEEPSEEK_API_KEY=          # 瀵硅瘽妯″瀷锛堜笉濉棤娉曡繍琛岋紝鏈」鐩病鏈夌绾垮厹搴曪級
DASHSCOPE_API_KEY=         # embedding锛坱ext-embedding-v4锛?024 缁达級
# EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
# DATABASE_URL=postgresql://smartdesk:smartdesk@localhost:5432/smartdesk
# MILVUS_URI=http://localhost:19530
```

> `.env` 宸插湪 `.gitignore` 閲岋紱AI 鍔╂墜涓嶈鍙栥€佷笉鎵撳嵃瀵嗛挜鍊硷紙鍔╂墜涓嶈鍙栥€佷笉鎵撳嵃瀵嗛挜鍊硷級銆?
### A.4 璧锋湇鍔?+ 鐏屾暟鎹?+ 璺戣捣鏉?
```bash
cd deploy && docker compose up -d                          # PG + Milvus + etcd + attu
.venv/Scripts/python.exe -m scripts.env_status       # 鍙湅"璁剧疆浜?娌¤缃?

# 鐭ヨ瘑搴撳叆搴擄紙绗竴娆″繀椤诲仛锛涘凡鍏ュ簱鍙烦杩囷級
.venv/Scripts/python.exe -m scripts.ingest_docs --md docs/kb/md --to-milvus --force

# 鐭ヨ瘑鍨?.venv/Scripts/python.exe -m scripts.run_graph run --thread t1 -m "鍙戠エ鎬庝箞寮€"
# 鍔ㄤ綔鍨嬶紙鍋滃湪纭闂級鈫?鏂拌繘绋嬬户缁?.venv/Scripts/python.exe -m scripts.run_graph run --thread t2 -m "甯垜寤轰釜宸ュ崟锛歏PN 杩炰笉涓?
.venv/Scripts/python.exe -m scripts.run_graph resume --thread t2 --approve
# 瀹℃壒鍨嬶紙鍏冲崟 + 閫氱煡锛岄渶瑕?approver 瑙掕壊锛?.venv/Scripts/python.exe -m scripts.run_graph run --thread t3 --role approver -m "鎶?TK-... 鍏虫帀锛岄『渚块€氱煡鎻愬崟浜?
# 閫愯妭鐐硅窡璇伙紙瀛︿範鐢級
.venv/Scripts/python.exe -m scripts.trace_run --thread t4 -m "鍙戠エ鎬庝箞寮€"
# 宸ュ叿娓呭崟 / 瀵煎嚭 mermaid 鍥?.venv/Scripts/python.exe -m scripts.run_graph tools
.venv/Scripts/python.exe -m scripts.run_graph graph   # 杈撳嚭 Mermaid锛屽彲閲嶅畾鍚戝埌浠绘剰 .mmd 鏂囦欢
```
## 闄勫綍 B锛氳绋嬭涔夊鐓т笌寤朵几闃呰

**11 浠借涔?鈫?鏈」鐩敤鍒扮殑鍦版柟**

| 璁蹭箟 | 瀵瑰簲绔犺妭 | 鐢ㄥ湪鏈」鐩摢閲?|
|---|---|---|
| 绗?鑺?LangChain鏍稿績缁勪欢 | 1.1 | 妯″瀷鎺ュ叆銆佸伐鍏枫€佺粨鏋勫寲杈撳嚭銆乧heckpointer銆佹憳瑕佷腑闂翠欢 |
| 绗?鑺?Agent鍏ラ棬瀹炴垬锛圓I绉佸帹锛?| 1.9銆?.4 | FastAPI 涓夊眰鎺ュ彛銆丼SE銆丼qliteSaver銆乴anggraph dev 鑱旇皟 |
| 绗?鑺?Runtime | 1.2 | 澶氱鎴?`UserContext`銆丼tate 鍐欏洖銆丼tore 瀛樺亸濂?|
| 绗?鑺?Middleware | 1.3 | PII 鑴辨晱銆佹ā鍨嬮檷绾с€丠ITL銆佹憳瑕?|
| 绗?鑺?MCP | 1.8 | 鍐呴儴绯荤粺缃戝叧銆佸姩鎬佹寕杞藉伐鍏?|
| 绗?鑺?Multi Agent | 1.5 | 瀛?Agent 鎷嗗垎锛堝彲閫夛級銆丼end 骞惰 |
| 绗?鑺?RAG Agent | 1.6 | 瑙ｆ瀽/鍒囧垎/embedding/2-Step vs Agentic |
| 绗?鑺?Milvus鍚戦噺搴?| 1.7 | 娣峰悎妫€绱€佺簿鎺掋€佽繃婊ゃ€丩angChain 闆嗘垚 |
| 绗?鑺?鍩烘湰姒傚康鍜屽叆闂?| 1.4 | StateGraph銆乺educer銆丆ommand銆乮nterrupt |
| 绗?鑺?甯歌WorkFlow | 1.4 | Routing銆丱rchestrator-Worker銆丼end銆丼ubgraphs |
| 绗?鑺?Think In LangGraph | 1.4 | 涓冭妭鐐规敮鎸?Agent銆佹渶灏忚竟銆佸紓甯稿垎绾с€丼tate 鐦﹁韩 |

**瀹樻柟鏂囨。锛堝啓浠ｇ爜鏃跺鐓э紝娉ㄦ剰璇剧▼鏄?1.x 鐗堟湰锛?*
- LangChain v1锛歔docs.langchain.com/oss/python/releases/langchain-v1](https://docs.langchain.com/oss/python/releases/langchain-v1)
- LangGraph v1锛歔docs.langchain.org.cn/oss/javascript/releases/langgraph-v1](https://docs.langchain.org.cn/oss/javascript/releases/langgraph-v1)
- Milvus 娣峰悎妫€绱笌閲嶆帓锛歔milvus.io/docs/zh/v2.6.x/reranking.md](https://milvus.io/docs/zh/v2.6.x/reranking.md)
- MCP 瀹樻柟瑙勮寖锛歔modelcontextprotocol.io](https://modelcontextprotocol.io)
- FastMCP 鏂囨。锛歔gofastmcp.com](https://gofastmcp.com)

---

## 缁撹锛氬鏋滃彧璁颁笁鍙ヨ瘽

1. **绠€鍘嗛」鐩殑浠峰€间笉鍦?鐢ㄤ簡澶氬皯鎶€鏈?锛岃€屽湪"浣犱负浠€涔堣繖涔堥€?+ 鏁板瓧璇佹槑閫夊浜?銆?*
2. **浼佷笟绾?= 鐘舵€佸彲鎭㈠锛坈heckpointer锛? 浜哄伐鍙粙鍏ワ紙interrupt锛? 鏁版嵁鍙殧绂伙紙澶氱鎴凤級+ 鏁堟灉鍙害閲忥紙璇勬祴锛夈€?* 杩欏洓浠朵簨鍋氬埌锛岄」鐩氨浠?璇剧▼浣滀笟"鍙樻垚"鐢熶骇鍘熷瀷"銆?3. **鍏堣窇閫氫富鍥?鈫?鍐嶈ˉ浼佷笟鍖?鈫?鏈€鍚庡仛璇勬祴涓庡寘瑁呫€?* 椤哄簭鍙嶄簡灏变細鍋氭垚姘歌繙涓婁笉浜嗙嚎鐨勫崐鎴愬搧銆?
