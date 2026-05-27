// 静态演示数据 · MVP 阶段
// 正式版会被后端 RSS 抓取 + NER 地理标签流水线替换
// key: 国家英文名（与 Natural Earth ADMIN 字段对齐）或 ISO_A2 代码
// 顺序固定：政治 → 军事 → 经济 → 科技 → 航空

const NEWS_DATA = {
  "China": {
    _meta: "2026-05-25 · 北京时间",
    politics: [
      { title: "国务院召开常务会议，部署二季度经济与就业重点工作", time: "2小时前", source: "新华社" },
      { title: "中美外长通话，就台海与南海问题交换意见", time: "5小时前", source: "外交部" },
      { title: "粤港澳大湾区建设领导小组第十次会议召开", time: "今日 09:00", source: "人民日报" }
    ],
    military: [
      { title: "海军第 46 批护航编队启航前往亚丁湾", time: "今日 09:30", source: "国防部" },
      { title: "解放军东部战区在台海周边组织联合战备警巡", time: "今日", source: "央视" }
    ],
    economy: [
      { title: "4 月制造业 PMI 50.4，连续三月位于扩张区间", time: "今日 09:00", source: "统计局" },
      { title: "央行公开市场净投放 800 亿元，DR007 小幅下行", time: "1小时前", source: "人民银行" },
      { title: "新能源车 1-4 月出口同比增长 28.6%", time: "昨日", source: "中汽协" }
    ],
    technology: [
      { title: "阿里通义 Qwen3 发布并开源 235B 旗舰模型", time: "昨日", source: "阿里云" },
      { title: "中芯国际 N+2 工艺良率突破，月产能爬坡至 3 万片", time: "3天前", source: "财新" },
      { title: "字节豆包推出多模态推理 API", time: "本周", source: "36氪" }
    ],
    aviation: [
      { title: "C919 完成首条国际商业航线试运营（上海-河内）", time: "今日 11:00", source: "中国商飞" },
      { title: "嫦娥七号月球南极任务确定 2026 年底窗口", time: "本周", source: "国家航天局" },
      { title: "天舟九号货运飞船与天宫空间站完成对接", time: "今日 03:48", source: "中国载人航天" }
    ]
  },

  "United States of America": {
    _meta: "2026-05-25 · UTC-5",
    politics: [
      { title: "白宫发布关于对华关税豁免清单调整的最新声明", time: "3小时前", source: "Reuters" },
      { title: "国会两党就 2027 财年国防授权法案达成框架协议", time: "今日", source: "AP" }
    ],
    military: [
      { title: "国防部宣布向西太平洋追加部署一批 F-35B", time: "今日 06:00", source: "Pentagon" },
      { title: "美军第七舰队在南海开展自由航行行动", time: "昨日", source: "USNI" }
    ],
    economy: [
      { title: "美联储 5 月议息会议维持利率不变，点阵图暗示年内一次降息", time: "1天前", source: "Fed" },
      { title: "标普 500 收涨 0.4%，纳指创年内新高", time: "昨日收盘", source: "Bloomberg" },
      { title: "苹果财报超预期，服务业务收入同比+14%", time: "本周", source: "WSJ" }
    ],
    technology: [
      { title: "OpenAI 发布 GPT 新一代企业版，支持百万 tokens 缓存", time: "今日", source: "OpenAI" },
      { title: "NVIDIA 发布 Blackwell Ultra GB300，推理性能提升 1.5x", time: "本周", source: "NVIDIA" },
      { title: "Anthropic Claude 4.7 上线，开放 1M context 商用", time: "本周", source: "Anthropic" }
    ],
    aviation: [
      { title: "SpaceX 星舰第 12 次试飞成功完成助推器与飞船双回收", time: "今日", source: "SpaceX" },
      { title: "Boeing 737 MAX 复飞认证扩展至沙特与印尼", time: "上周", source: "FAA" },
      { title: "NASA 阿尔忒弥斯 III 推迟至 2027 年 Q3", time: "昨日", source: "NASA" }
    ]
  },

  "Russia": {
    _meta: "2026-05-25 · 莫斯科时间",
    politics: [
      { title: "克里姆林宫就乌克兰停火谈判最新进展表态", time: "4小时前", source: "TASS" },
      { title: "俄外长访问北京，将与中方讨论上合组织峰会议程", time: "今日", source: "Sputnik" }
    ],
    military: [
      { title: "俄军在黑海方向部署新一批苏-57 与 S-500", time: "今日", source: "国防部" },
      { title: "黑海舰队完成例行实弹演习", time: "昨日", source: "RIA" }
    ],
    economy: [
      { title: "俄央行维持基准利率 16%，通胀预期下调", time: "昨日", source: "央行" },
      { title: "卢布对人民币汇率创年内新高", time: "今日", source: "MOEX" }
    ],
    technology: [
      { title: "Yandex 开源新一代搜索算法 YaLM-Search", time: "本周", source: "Yandex" }
    ],
    aviation: [
      { title: "联盟 MS-29 载人飞船与国际空间站成功对接", time: "今日 03:00", source: "Roscosmos" },
      { title: "苏霍伊超级喷气-100 完成出口印度首批交付", time: "本周", source: "UAC" }
    ]
  },

  "Japan": {
    _meta: "2026-05-25 · 东京时间",
    politics: [
      { title: "首相官邸召开国家安全保障会议讨论台海议题", time: "今日", source: "NHK" },
      { title: "日韩外长会晤，就福岛核处理水问题继续磋商", time: "昨日", source: "朝日" }
    ],
    military: [
      { title: "自卫队与美军举行联合实弹演习「东方之盾 2026」", time: "本周", source: "防卫省" }
    ],
    economy: [
      { title: "日银议息会议保持当前货币政策，加息预期推迟", time: "昨日", source: "日银" },
      { title: "日元兑美元跌破 158", time: "今日", source: "日经" }
    ],
    technology: [
      { title: "索尼发布下一代车载图像传感器 IMX-900", time: "本周", source: "Sony" },
      { title: "丰田与 SoftBank 联合发布自动驾驶平台", time: "昨日", source: "日经" }
    ],
    aviation: [
      { title: "JAXA H3 火箭第 8 次发射成功，搭载月球探测器", time: "今日", source: "JAXA" }
    ]
  },

  "Germany": {
    _meta: "2026-05-25 · 柏林时间",
    politics: [
      { title: "德国联邦议院通过新一轮对乌援助方案", time: "今日", source: "DW" }
    ],
    military: [
      { title: "德军「豹 2A8」首批 18 辆交付立陶宛前沿部队", time: "本周", source: "BMVg" }
    ],
    economy: [
      { title: "德国一季度 GDP 环比+0.2%，重回扩张", time: "昨日", source: "Destatis" },
      { title: "大众宣布扩大与小鹏在欧洲市场的合作", time: "今日", source: "Handelsblatt" }
    ],
    technology: [
      { title: "SAP 推出企业 AI Agent 平台 Joule X", time: "本周", source: "SAP" }
    ],
    aviation: [
      { title: "空客 A350F 货机首飞测试在汉堡完成", time: "今日", source: "Airbus" }
    ]
  },

  "United Kingdom": {
    _meta: "2026-05-25 · 伦敦时间",
    politics: [
      { title: "英国首相宣布提前举行内阁改组", time: "今日", source: "BBC" }
    ],
    military: [
      { title: "皇家海军「威尔士亲王」号航母编队启航印太", time: "本周", source: "MoD" }
    ],
    economy: [
      { title: "英国央行维持利率 4.25%，通胀回落至 2.3%", time: "昨日", source: "BoE" }
    ],
    technology: [
      { title: "DeepMind 发布蛋白质设计模型 AlphaFold 4", time: "本周", source: "Nature" }
    ],
    aviation: [
      { title: "罗罗 UltraFan 发动机完成全功率台架试验", time: "今日", source: "Rolls-Royce" }
    ]
  },

  "France": {
    _meta: "2026-05-25 · 巴黎时间",
    politics: [
      { title: "马克龙访问北京，签署多领域合作协议", time: "本周", source: "Le Monde" }
    ],
    military: [
      { title: "「戴高乐」号航母赴地中海部署", time: "今日", source: "Marine" }
    ],
    economy: [
      { title: "法国 4 月 CPI 同比+1.9%，回到目标区间", time: "昨日", source: "INSEE" }
    ],
    technology: [
      { title: "Mistral 发布开源旗舰模型 Mistral Large 3", time: "本周", source: "Mistral" }
    ],
    aviation: [
      { title: "阿丽亚娜 6 号成功发射伽利略系统三颗卫星", time: "今日", source: "ESA" }
    ]
  },

  "India": {
    _meta: "2026-05-25 · 新德里时间",
    politics: [{ title: "印度总理访问东京，签署稀土供应链协议", time: "今日", source: "TOI" }],
    military: [{ title: "印度海军「维克兰特」号航母完成第二阶段海试", time: "本周", source: "PIB" }],
    economy: [{ title: "印度一季度 GDP 增长 7.4%，超出市场预期", time: "昨日", source: "RBI" }],
    technology: [{ title: "Reliance Jio 推出全国性 AI 助理服务", time: "本周", source: "Economic Times" }],
    aviation: [{ title: "ISRO 月船 4 号任务确认 2026 年底发射", time: "今日", source: "ISRO" }]
  },

  "South Korea": {
    _meta: "2026-05-25 · 首尔时间",
    politics: [{ title: "韩美元首通话讨论朝鲜半岛安全形势", time: "今日", source: "Yonhap" }],
    military: [{ title: "韩军 KF-21「猎鹰」量产首架机下线", time: "本周", source: "KAI" }],
    economy: [{ title: "韩国央行降息 25 个基点至 3.25%", time: "昨日", source: "BoK" }],
    technology: [{ title: "三星 3nm GAA 良率提升至 60%", time: "本周", source: "ChosunBiz" }],
    aviation: [{ title: "韩国 KSLV-III 火箭完成第一级静态点火", time: "今日", source: "KARI" }]
  },

  "Ukraine": {
    _meta: "2026-05-25 · 基辅时间",
    politics: [{ title: "泽连斯基会见到访的欧盟外交与安全政策高级代表", time: "今日", source: "Ukrinform" }],
    military: [{ title: "乌军在哈尔科夫方向开展无人机集群打击", time: "今日", source: "ISW" }],
    economy: [{ title: "IMF 批准对乌新一轮 11 亿美元援助", time: "昨日", source: "IMF" }],
    technology: [],
    aviation: [{ title: "安东诺夫宣布 An-178 货机重启生产线", time: "本周", source: "Antonov" }]
  },

  "Israel": {
    _meta: "2026-05-25 · 耶路撒冷时间",
    politics: [{ title: "以色列内阁批准与沙特关系正常化路线图", time: "今日", source: "Haaretz" }],
    military: [{ title: "以军「铁穹」系统拦截多枚火箭弹", time: "今日", source: "IDF" }],
    economy: [{ title: "以色列科技板块上市公司一季度营收增长 18%", time: "本周", source: "Globes" }],
    technology: [{ title: "Mobileye 发布下一代自动驾驶芯片 EyeQ7", time: "本周", source: "Mobileye" }],
    aviation: [{ title: "IAI 与印度签署预警机出口框架协议", time: "今日", source: "IAI" }]
  },
};
