const API = "http://localhost:8000";

export async function getCategories() {
  const r = await fetch(`${API}/booking/categories`);
  return r.json();
}

export async function getServices(categoryId) {
  const r = await fetch(`${API}/booking/services?category_id=${categoryId}`);
  return r.json();
}

export async function getSlots(serviceIds, duration, date, serviceId = 0) {
  const r = await fetch(`${API}/booking/slots?date=${date}&duration=${duration}&service_id=${serviceId}`);
  return r.json();
}

export async function getStaff(serviceIds, datetime, duration, serviceId = 0) {
  const r = await fetch(`${API}/booking/staff?datetime=${encodeURIComponent(datetime)}&duration=${duration}&service_id=${serviceId}`);
  return r.json();
}

export async function createBooking(data) {
  const r = await fetch(`${API}/booking/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  });
  return r.json();
}

export async function getNearestSlot(duration, serviceId = 0) {
  const r = await fetch(`${API}/booking/nearest_slot?duration=${duration}&service_id=${serviceId}`);
  return r.json();
}

export async function getBooking(bookingId) {
  const r = await fetch(`${API}/booking/booking/${bookingId}`);
  return r.json();
}

