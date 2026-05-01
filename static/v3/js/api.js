// ============ API ============

async function fetchData(url) {
  try {
    const res = await fetch(API + url);
    return await res.json();
  } catch (e) {
    console.error('Fetch error:', url, e);
    return null;
  }
}
