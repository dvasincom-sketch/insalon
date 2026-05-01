import { useEffect, useState } from "react";
import { getCategories } from "../api/booking";

const HIDDEN = ["Без группы", "Напитки", "Дополнительные услуги"];

export default function Categories({ next }) {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCategories().then((data) => {
      setCategories(data.filter((c) => !HIDDEN.includes(c.title)));
      setLoading(false);
    });
  }, []);

  if (loading) return <p>Загрузка...</p>;

  return (
    <div>
      <h2>Выберите категорию</h2>
      {categories.map((cat) => (
        <div
          key={cat.id}
          onClick={() => next({ category: cat })}
          style={{
            border: "1px solid #ddd",
            borderRadius: 8,
            padding: 16,
            marginBottom: 12,
            cursor: "pointer",
          }}
        >
          <strong>{cat.title}</strong>
        </div>
      ))}
    </div>
  );
}
