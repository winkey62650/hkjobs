import OpenAI from "openai";

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "POST")
    return res.status(405).json({ error: "Method not allowed" });

  const { jd, experiences, background, name } = req.body || {};
  if (!jd) return res.status(400).json({ error: "Missing JD" });

  const client = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
    baseURL: process.env.OPENAI_BASE_URL || "https://api.xiaomimimo.com/v1",
  });

  const expText =
    experiences && experiences.length
      ? experiences
          .map(
            (x, i) =>
              `Experience ${i + 1}: ${x.position} at ${x.company}\nExisting bullets:\n${x.bullets || "(none yet)"}`
          )
          .join("\n\n")
      : "(No experience yet — generate general bullets based on the background)";

  const prompt = `You are a Hong Kong professional CV & cover-letter writing expert.

CANDIDATE NAME: ${name || "the candidate"}

CANDIDATE BACKGROUND:
${background || "BA in English, MA in Philosophy, fresh graduate"}

CANDIDATE'S EXPERIENCE ENTRIES:
${expText}

TARGET JOB DESCRIPTION:
${jd}

TASK:
For each experience entry, rewrite or generate 3–5 bullet points that:
1. Use strong action verbs (Drafted, Analysed, Coordinated, Developed, etc.)
2. Incorporate keywords and requirements from the JD naturally
3. Include measurable results where possible (e.g. "reduced turnaround by 30%")
4. Are concise and appropriate for Hong Kong professional CVs
5. Are in English

Also generate:
- A tailored OBJECTIVE paragraph (2–3 sentences) that directly responds to this specific JD
- A SKILLS line: 6–8 comma-separated skills the candidate should highlight, drawn from the JD requirements and matched to the candidate's background (mix of hard and soft skills)
- 5 key keywords extracted from the JD
- COMPANY: the hiring company name extracted from the JD ("" if not stated)
- ROLE: the job title extracted from the JD ("" if not stated)
- A COVER LETTER body — exactly 3 concise paragraphs, ~220–280 words total, English, Hong Kong professional tone:
  P1: interest in the role + a one-line summary of why the candidate fits
  P2: 2–3 specific qualifications/achievements from the candidate's background mapped to the JD's key requirements
  P3: enthusiasm to contribute + a polite call to action
  Write the BODY ONLY — no date, no "Dear ..." line, no sign-off. Separate the 3 paragraphs with a blank line.

OUTPUT FORMAT — respond only with valid JSON, no markdown fences:
{
  "objective": "...",
  "experiences": [
    { "index": 0, "bullets": ["bullet 1", "bullet 2", "bullet 3"] }
  ],
  "skills": "skill1, skill2, skill3, skill4, skill5, skill6",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "company": "...",
  "roleTitle": "...",
  "coverLetter": "First paragraph...\\n\\nSecond paragraph...\\n\\nThird paragraph..."
}`;

  try {
    const completion = await client.chat.completions.create({
      model: "mimo-v2.5",
      max_tokens: 4000,
      messages: [
        {
          role: "system",
          content: "You are a professional Hong Kong CV writer. Always respond with valid JSON only.",
        },
        { role: "user", content: prompt },
      ],
    });

    const text = completion.choices[0].message.content.trim();

    // 提取 JSON：去掉 markdown 围栏，找到第一个 { ... }
    let cleaned = text.replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/```\s*$/i, "").trim();

    // 找到最外层 JSON 对象
    const start = cleaned.indexOf("{");
    let end = cleaned.lastIndexOf("}");
    if (start === -1) throw new Error("No JSON object in response");

    // 如果 JSON 被截断，尝试修复
    let jsonStr = cleaned.slice(start, end + 1);
    let result;
    try {
      result = JSON.parse(jsonStr);
    } catch {
      // 截断修复：找到最后一个完整字段
      const truncated = cleaned.slice(start);
      // 构造最小可用结构
      const unesc = s => String(s || "")
        .replace(/\\n/g, "\n").replace(/\\"/g, '"').replace(/\\\\/g, "\\");
      const objMatch = truncated.match(/"objective"\s*:\s*"((?:[^"\\]|\\.)*)"/);
      const skMatch  = truncated.match(/"skills"\s*:\s*"((?:[^"\\]|\\.)*)"/);
      const clMatch  = truncated.match(/"coverLetter"\s*:\s*"((?:[^"\\]|\\.)*)"/);
      const coMatch  = truncated.match(/"company"\s*:\s*"((?:[^"\\]|\\.)*)"/);
      const rtMatch  = truncated.match(/"roleTitle"\s*:\s*"((?:[^"\\]|\\.)*)"/);
      const kwMatch  = truncated.match(/"keywords"\s*:\s*\[([^\]]*)\]/);
      const bullets  = [];
      const bulMatch = truncated.matchAll(/"bullets"\s*:\s*\[([^\]]*)\]/g);
      for (const m of bulMatch) {
        const items = m[1].match(/"((?:[^"\\]|\\.)*)"/g) || [];
        bullets.push({ index: bullets.length, bullets: items.map(s => unesc(s.replace(/^"|"$/g, ""))) });
      }
      result = {
        objective: objMatch ? unesc(objMatch[1]) : "",
        experiences: bullets,
        skills: skMatch ? unesc(skMatch[1]) : "",
        keywords: kwMatch ? kwMatch[1].match(/"([^"]*)"/g)?.map(s => s.replace(/^"|"$/g,"")) || [] : [],
        company: coMatch ? unesc(coMatch[1]) : "",
        roleTitle: rtMatch ? unesc(rtMatch[1]) : "",
        coverLetter: clMatch ? unesc(clMatch[1]) : "",
      };
    }

    res.status(200).json(result);
  } catch (err) {
    console.error("API Error:", err.message);
    res.status(500).json({ error: err.message });
  }
}
