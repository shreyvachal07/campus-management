const fallbackEvents = [
  ['Mindfulness & Sound Bath Meditation', 'Today Â· 3:00 PM', 'Wellness Studio', 'https://images.unsplash.com/photo-1545389336-cf090694435e?auto=format&fit=crop&w=700&q=80', 'RSVP now'],
  ['Engineering Hackathon & Career Mentorship', 'Wed, Oct 23 Â· 10:00 AM', 'Innovation Hub', 'https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=700&q=80', 'Get pass'],
  ['Campus Farmers Market & Nutrition Demo', 'Thu, Oct 24 Â· 11:00 AM', 'Central Lawn', 'https://images.unsplash.com/photo-1531058020387-3be344556be6?auto=format&fit=crop&w=700&q=80', 'Save event'],
  ['Late-Night Study CafÃ©: Peer Exam Prep', 'Thu, Oct 24 Â· 7:00 PM', 'Library commons', 'https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=700&q=80', 'RSVP now'],
  ['First-Gen Student Peer Connection Dinner', 'Fri, Oct 25 Â· 6:30 PM', 'Maple Hall', 'https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=700&q=80', 'Join dinner'],
  ['Sunset Yoga on the Great Lawn', 'Sat, Oct 26 Â· 6:00 PM', 'Great Lawn', 'https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=700&q=80', 'RSVP now']
];
const apiBase = window.CAMPUS_API_URL || (location.protocol === 'file:' ? 'http://localhost:5000' : location.origin);
const eventImages = [
  'https://images.unsplash.com/photo-1545389336-cf090694435e?auto=format&fit=crop&w=700&q=80',
  'https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=700&q=80',
  'https://images.unsplash.com/photo-1531058020387-3be344556be6?auto=format&fit=crop&w=700&q=80',
  'https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=700&q=80'
];

function renderEvents(events) {
  document.querySelector('#eventGrid').innerHTML = events.map(([title,time,place,img,action, id]) => `<article class="event-card"><img src="${img}" alt="" /><div><h3>${title}</h3><p>â—· ${time}</p><p>âŒ– ${place}</p><footer><span>â™¡</span><button data-event-id="${id || ''}">${action}</button></footer></div></article>`).join('');
  document.querySelectorAll('.event-card button').forEach(button => button.addEventListener('click', () => register(button)));
}

async function loadEvents() {
  try {
    const response = await fetch(`${apiBase}/api/events?limit=6`);
    if (!response.ok) throw new Error('Could not load events');
    const { data } = await response.json();
    if (!data.length) return renderEvents(fallbackEvents);
    renderEvents(data.map((event, index) => [event.title, event.status === 'open' ? 'Open for registration' : 'Coming soon', `${event.capacity} places available`, eventImages[index % eventImages.length], 'RSVP now', event.id]));
  } catch (_) {
    renderEvents(fallbackEvents);
  }
}

async function register(button) {
  const userId = window.CAMPUS_USER_ID;
  const eventId = button.dataset.eventId;
  if (!eventId) return alert('This demo event is not connected to the database yet.');
  if (!userId) return alert('Set CAMPUS_USER_ID after sign-in before registering for an event.');
  try {
    const response = await fetch(`${apiBase}/api/registrations`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: userId, event_id: eventId }) });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || 'Registration failed');
    button.textContent = 'âœ“ Youâ€™re going';
    button.disabled = true;
  } catch (error) { alert(error.message); }
}

loadEvents();
document.querySelectorAll('.filters button').forEach(button => button.addEventListener('click', () => { document.querySelector('.filters .active').classList.remove('active'); button.classList.add('active'); }));
document.querySelector('.rsvp').addEventListener('click', e => { e.currentTarget.textContent = 'âœ“ Youâ€™re going'; e.currentTarget.classList.add('confirmed'); });

