import { useState } from "react";
import Categories from "./pages/Categories";
import Services from "./pages/Services";
import Extras from "./pages/Extras";
import DateTime from "./pages/DateTime";
import Master from "./pages/Master";
import Contacts from "./pages/Contacts";
import Success from "./pages/Success";

const STEPS = ["categories", "services", "extras", "datetime", "master", "contacts", "success"];

export default function App() {
  const params = new URLSearchParams(window.location.search);
  const [step, setStep] = useState(params.get("booking_id") ? "success" : "categories");
  const [booking, setBooking] = useState({
    category: null,
    service: null,
    extras: [],
    datetime: null,
    master: null,
    contact: null,
    paymentUrl: null,
  });

  const next = (data) => {
    setBooking((prev) => ({ ...prev, ...data }));
    const idx = STEPS.indexOf(step);
    setStep(STEPS[idx + 1]);
  };

  const back = () => {
    const idx = STEPS.indexOf(step);
    if (idx > 0) setStep(STEPS[idx - 1]);
  };

  const props = { booking, next, back };

  return (
    <div style={{ maxWidth: 600, margin: "0 auto", padding: 24, fontFamily: "sans-serif" }}>
      {step === "categories" && <Categories {...props} />}
      {step === "services" && <Services {...props} />}
      {step === "extras" && <Extras {...props} />}
      {step === "datetime" && <DateTime {...props} />}
      {step === "master" && <Master {...props} />}
      {step === "contacts" && <Contacts {...props} />}
      {step === "success" && <Success {...props} />}
    </div>
  );
}
