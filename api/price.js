/* eslint-disable no-undef */
module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'POST only' });
    return;
  }
  try {
    const { item, float, paintSeed } = req.body;
    if (!item) { res.status(400).json({ error: 'Missing item' }); return; }

    // — Wear bucket helper —
    const BUCKETS = [
      [0.00, 0.07, 'Factory New'],
      [0.07, 0.15, 'Minimal Wear'],
      [0.15, 0.38, 'Field-Tested'],
      [0.38, 0.45, 'Well-Worn'],
      [0.45, 1.00, 'Battle-Scarred']
    ];
    const classifyWear = v => {
      for (const [lo, hi, name] of BUCKETS) if (v >= lo && v < hi) return name;
      throw new Error('Float out of range');
    };

    const wear = float ? classifyWear(parseFloat(float)) : 'Factory New';
    const hashName = `${item} (${wear})`;

    // — Steam baseline —
    const steamParams = new URLSearchParams({ appid: '730', currency: '1', market_hash_name: hashName });
    const steamRes = await fetch(`https://steamcommunity.com/market/priceoverview/?${steamParams}`);
    if (!steamRes.ok) throw new Error('Steam request failed');
    const steamData = await steamRes.json();
    const num = s => s ? parseFloat(s.replace(/[^\d.]/g, '')) : undefined;
    const median = num(steamData.median_price);
    const lowest = num(steamData.lowest_price);

    // — CSFloat for float‑precise premium —
    let floatAvg;
    const key = process.env.CSFLOAT_API_KEY;
    if (key && float) {
      const f = parseFloat(float); const w = 0.002;
      const qs = new URLSearchParams({
        market_hash_name: hashName,
        sort_by: 'lowest_price',
        limit: '50',
        min_float: Math.max(f - w, 0),
        max_float: Math.min(f + w, 1)
      });
      if (paintSeed) qs.set('paint_seed', paintSeed);
      const csRes = await fetch(`https://csfloat.com/api/v1/listings?${qs}`, { headers: { Authorization: key } });
      if (csRes.ok) {
        const listings = await csRes.json();
        if (listings.length) floatAvg = listings.reduce((s, l) => s + l.price, 0) / 100 / listings.length;
      }
    }

    const expected = floatAvg ?? median ?? lowest;
    if (expected === undefined) throw new Error('No price data found');
    res.json({ expectedPrice: expected });
  } catch (err) {
    res.status(500).json({ error: err.message || 'Internal error' });
  }
};