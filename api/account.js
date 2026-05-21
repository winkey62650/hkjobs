// 秒投 — 简单账号系统（账号码登录）
// 数据存 Upstash / Vercel KV（Redis REST API，用 fetch 直连，无需 npm 包）
// POST { action: 'create' | 'load' | 'save', id?, profiles? }

const KV_URL =
  process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL || "";
const KV_TOKEN =
  process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN || "";

// 执行一条 Redis 命令（Upstash REST：POST 根 URL，body 为命令数组）
async function kv(cmd) {
  const r = await fetch(KV_URL, {
    method: "POST",
    headers: {
      Authorization: "Bearer " + KV_TOKEN,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(cmd),
  });
  if (!r.ok) throw new Error("KV " + r.status);
  return (await r.json()).result;
}

// 生成账号码：mt- + 8 位（去掉易混字符 0/1/o/l/i）
function newCode() {
  const chars = "23456789abcdefghjkmnpqrstuvwxyz";
  let s = "";
  for (let i = 0; i < 8; i++)
    s += chars[Math.floor(Math.random() * chars.length)];
  return "mt-" + s;
}

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "POST")
    return res.status(405).json({ error: "Method not allowed" });

  if (!KV_URL || !KV_TOKEN)
    return res
      .status(500)
      .json({ error: "数据库未配置：请在 Vercel 后台连接 KV / Redis 存储" });

  const body = req.body || {};
  const action = body.action;
  const id = String(body.id || "").trim().toLowerCase();
  const today = new Date().toISOString().slice(0, 10);

  try {
    // ── 新建账号 ──────────────────────────────────────────────────────────
    if (action === "create") {
      let code = newCode();
      for (let i = 0; i < 6 && (await kv(["GET", "acct:" + code])); i++)
        code = newCode();
      const account = { created: today, profiles: [] };
      await kv(["SET", "acct:" + code, JSON.stringify(account)]);
      return res.status(200).json({ id: code, account });
    }

    // ── 登录 / 读取 ───────────────────────────────────────────────────────
    if (action === "load") {
      if (!id) return res.status(400).json({ error: "请输入账号码" });
      const raw = await kv(["GET", "acct:" + id]);
      if (!raw) return res.status(404).json({ error: "账号码不存在" });
      return res.status(200).json({ id, account: JSON.parse(raw) });
    }

    // ── 保存资料（最多 2 个名字）─────────────────────────────────────────
    if (action === "save") {
      if (!id) return res.status(400).json({ error: "请输入账号码" });
      const raw = await kv(["GET", "acct:" + id]);
      if (!raw) return res.status(404).json({ error: "账号码不存在" });
      const account = JSON.parse(raw);
      account.profiles = Array.isArray(body.profiles)
        ? body.profiles.slice(0, 2) // 服务端强制：每个账号最多 2 个名字
        : [];
      account.updated = today;
      await kv(["SET", "acct:" + id, JSON.stringify(account)]);
      return res.status(200).json({ ok: true, account });
    }

    return res.status(400).json({ error: "未知操作" });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}
