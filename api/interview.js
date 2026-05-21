import OpenAI from "openai";

// 推理模型较慢，给足执行时间
export const config = { maxDuration: 60 };

const CHAT_SYS = `你是一位亲切、专业的求职顾问，正在帮一位香港求职者回忆并梳理过往经历，为写简历做准备。
你要通过对话，帮他想起并讲清楚三方面：
1. 学校与所学 —— 专业、印象深的课程、学到的知识与技能、课程作业或项目；
2. 工作 / 实习经历 —— 职位、日常职责、具体做过的事、可量化的成果；
3. 项目经历 —— 项目名称、他的角色、用到的技能、最终结果。

规则：
- 每次只问「一个」问题，简短自然；
- 根据他的回答深入追问细节，尤其是「具体做了什么」「有没有数字 / 成果」「你个人负责哪一部分」；
- 用中文，口吻亲切、鼓励、口语化，像朋友聊天，不要长篇大论、不要列清单；
- 如果回答含糊，温和地引导他想得更具体；
- 一个话题聊得差不多了，自然过渡到下一个（学校 → 工作 → 项目）；
- 三方面都聊过之后，提示他可以点「整理成简历」。`;

const EXTRACT_SYS = `你是香港专业简历顾问。根据下面的访谈对话，把求职者的经历整理成结构化的简历素材。
要求：
- 输出英文（香港求职 CV 标准）；
- bullet 用强动词开头（Drafted / Coordinated / Analysed 等），尽量包含可量化成果；
- 只整理对话中真实出现的信息，不要编造；某一类没有就给空数组。
只输出 JSON，不要 markdown 围栏：
{
  "education":[{"degree":"","school":"","period":"","detail":"relevant modules / thesis"}],
  "experience":[{"position":"","company":"","period":"","bullets":["bullet 1","bullet 2"]}],
  "projects":[{"name":"","context":"course / personal / 时间","bullets":["bullet 1","bullet 2"]}],
  "skills":"skill1, skill2, skill3"
}`;

const ONBOARD_SYS = `你是香港专业简历顾问。求职者刚填了基本信息，可能是中文、口语化、不规范。
请把它整理成「香港求职 CV 标准」的英文结构化数据：
- 学位用规范英文：例「硕士 + 统计学」→「Master of Science in Statistics」，「学士 + 英文」→「Bachelor of Arts in English」；
- 学校用通用英文名：例「马来亚大学」→「University of Malaya」，「香港中文大学」→「The Chinese University of Hong Kong」；
- 过往职业整理成英文 experience 条目，每条 2-4 个 bullet，强动词开头；信息不足就写合理的通用职责，绝不要编造具体数字；
- 写一段 2-3 句英文 OBJECTIVE，结合其学历与背景；
- 给 6-8 个相关英文技能；
- 英文名保持求职者填写的写法；
- 任何未提供的字段（如 period、detail）一律留「空字符串」，绝不要填 "Not Specified"、"N/A"、"TBD" 等占位词。
只输出 JSON，不要 markdown 围栏：
{
  "nameEn":"",
  "objective":"",
  "education":[{"degree":"","school":"","period":"","detail":""}],
  "experience":[{"position":"","company":"","period":"","bullets":["bullet 1","bullet 2"]}],
  "skills":"skill1, skill2, skill3"
}`;

function parseJsonObject(content) {
  let t = String(content || "").trim()
    .replace(/^```json\s*/i, "").replace(/^```\s*/i, "")
    .replace(/```\s*$/i, "").trim();
  const s = t.indexOf("{"), e = t.lastIndexOf("}");
  if (s === -1) throw new Error("AI 未返回有效结果");
  return JSON.parse(t.slice(s, e + 1));
}

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "POST")
    return res.status(405).json({ error: "Method not allowed" });

  const { mode, messages } = req.body || {};
  const history = Array.isArray(messages) ? messages : [];

  const client = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
    baseURL: process.env.OPENAI_BASE_URL || "https://api.xiaomimimo.com/v1",
  });

  try {
    // ── 对话模式 ──────────────────────────────────────────────────────────
    if (mode === "chat") {
      const msgs = [{ role: "system", content: CHAT_SYS }];
      if (history.length) {
        msgs.push(...history);
      } else {
        // 还没开始 —— 让 AI 先做简短自我介绍并问第一个问题
        msgs.push({ role: "user", content: "（请开始访谈：先用一两句话简短介绍你会怎么帮我，然后问第一个问题）" });
      }
      const completion = await client.chat.completions.create({
        model: "mimo-v2.5",
        max_tokens: 1500,
        messages: msgs,
      });
      const reply = completion.choices[0].message.content.trim();
      return res.status(200).json({ reply });
    }

    // ── 整理模式 ──────────────────────────────────────────────────────────
    if (mode === "extract") {
      const convo = history
        .map((m) => (m.role === "user" ? "求职者" : "顾问") + "：" + m.content)
        .join("\n");
      const completion = await client.chat.completions.create({
        model: "mimo-v2.5",
        max_tokens: 4000,
        messages: [
          { role: "system", content: EXTRACT_SYS },
          { role: "user", content: "访谈对话如下：\n\n" + convo },
        ],
      });
      let text = completion.choices[0].message.content.trim();
      text = text
        .replace(/^```json\s*/i, "")
        .replace(/^```\s*/i, "")
        .replace(/```\s*$/i, "")
        .trim();
      const start = text.indexOf("{");
      const end = text.lastIndexOf("}");
      if (start === -1) throw new Error("AI 未返回有效结果");
      let result;
      try {
        result = JSON.parse(text.slice(start, end + 1));
      } catch {
        // 兜底：尽量取出能用的部分
        result = { education: [], experience: [], projects: [], skills: "" };
      }
      result.education = result.education || [];
      result.experience = result.experience || [];
      result.projects = result.projects || [];
      result.skills = result.skills || "";
      return res.status(200).json(result);
    }

    // ── 进站引导整理：原始信息 → 规范英文简历字段 ────────────────────────
    if (mode === "onboard") {
      const a = req.body.answers || {};
      const raw =
        "姓名：" + (a.name || "") + "\n电邮：" + (a.email || "") +
        "\n学历：" + (a.level || "") + "\n学校：" + (a.school || "") +
        "\n专业：" + (a.major || "") + "\n过往职业：" + (a.jobs || "");
      const completion = await client.chat.completions.create({
        model: "mimo-v2.5",
        max_tokens: 3500,
        messages: [
          { role: "system", content: ONBOARD_SYS },
          { role: "user", content: "求职者填写的原始信息如下：\n\n" + raw },
        ],
      });
      let result;
      try {
        result = parseJsonObject(completion.choices[0].message.content);
      } catch {
        result = {};
      }
      result.nameEn = result.nameEn || a.name || "";
      result.objective = result.objective || "";
      result.education = result.education || [];
      result.experience = result.experience || [];
      result.skills = result.skills || "";
      return res.status(200).json(result);
    }

    return res.status(400).json({ error: "未知 mode" });
  } catch (err) {
    console.error("interview error:", err.message);
    return res.status(500).json({ error: err.message });
  }
}
