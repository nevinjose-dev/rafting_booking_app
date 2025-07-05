// static/script.js
document.addEventListener("DOMContentLoaded", () => {
  const peopleInput = document.querySelector("input[name='people']");
  const dateInput = document.querySelector("input[name='date']");
  const outputDiv = document.getElementById("price-summary");

  function updatePrice() {
    const people = parseInt(peopleInput.value);
    const date = new Date(dateInput.value);
    if (!people || !date) return;

    const day = date.getDay();
    const isWeekend = day === 0 || day === 6;
    const rate = isWeekend ? 1400 : 1300;
    const total = people * rate;

    let advance = 0;
    if (isWeekend) {
      advance = Math.floor(total / 2);
    } else {
      if (people >= 5 && people <= 6) advance = 1000;
      else if (people <= 12) advance = 2000;
      else if (people <= 18) advance = 3000;
    }

    outputDiv.innerHTML = `
      <p><strong>Total: ₹${total}</strong></p>
      <p><strong>Advance Payment: ₹${advance}</strong></p>
      <p><strong>Remaining: ₹${total - advance}</strong></p>
    `;
  }

  peopleInput.addEventListener("input", updatePrice);
  dateInput.addEventListener("change", updatePrice);
});
