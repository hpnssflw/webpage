# Landing Page — план для реализации (простой HTML/CSS, без React)

> **Историческая заметка:** этот документ — исходный план, дальше сайт
> разошёлся с ним в деталях. FOCUS переименован в RESEARCHER; секция
> "Агент-куратор контента для LAB" (п.5) реализована как отдельная
> инициатива — см. `PROGRESS.md` и `docs/agent-plan.md`. Актуальную
> структуру сайта смотри в `README.md`.

Бренд: Digital Craftsman (Artem Polozov) + LAB-блог (YEAHBALATORY / рабочее название)
Референс визуала: letta.com — только палитра, шрифты, общая композиция. Нарратив свой.

## 1. Дизайн-токены

**Цвета**
- Фон: `#202020` (тёмный, почти чёрный, не чистый #000)
- Текст основной: `#F5F5F5` / `#EDEDED` (не чистый белый — мягче на тёмном фоне)
- Текст вторичный/приглушённый (даты, мелкие подписи): `#8A8A8A`
- Акцентного цвета нет — сайт монохромный по замыслу. Ссылки — подчёркивание при hover, без цветового акцента
- Тонкая grid-текстура фоном (едва заметная, SVG или CSS `background-image` с низкой opacity ~0.03–0.05)

**Типографика**
- Основной шрифт: нейтральный sans-serif без засечек (например Inter, Helvetica Neue, или system-ui как фоллбек)
- Моноширинный шрифт для технических строк (`$ whoami`, контакты, даты в LAB-фиде) — например JetBrains Mono, IBM Plex Mono, или monospace фоллбек
- Крупный интерлиньяж (line-height ~1.6–1.7) — воздух важнее плотности
- Заголовки секций (если будут) — капсом, letter-spacing чуть увеличен, некрупный кегль (это не h1, а скорее лейбл)

**Общая композиция**
- Без карточек, теней, границ, скруглений — плоские текстовые блоки, разделённые только отступами
- Максимальная ширина контента ~600–720px, всё остальное — воздух по бокам (даже на десктопе), под "лабораторный журнал", не "маркетинговый лендинг"
- Мобильная версия: тот же максимум простоты — один столбец, без адаптивных хитростей, просто уменьшенные отступы/кегль

## 2. Структура страницы (сверху вниз)

### Секция 1 — Hero
```html
<section id="hero">
  <p class="role">Digital Craftsman</p>
  <h1>Artem Polozov</h1>
  <p class="hero-text">
    Web products, data visualization, systems integration, AI agent
    orchestration — same instinct applied to different systems: understand
    how it fails, then build so it doesn't.
  </p>
  <p class="contact mono">
    <a href="mailto:artem@...">artem@...</a> · <a href="https://github.com/hpnssflw">github.com/hpnssflw</a>
  </p>
</section>
```
Порядок элементов: роль (маленьким капсом над именем) → имя (крупно) → описание (абзац) → контакты (моноширинным внизу). Много вертикального отступа перед и после секции.

### Секция 2 — LAB (блог-фид)
```html
<section id="lab">
  <p class="section-label">LAB</p>
  <ul class="feed">
    <li>
      <a href="/lab/cheap-models-strong-graphs">
        <span class="mono date">AUG 2026</span>
        <span class="title">Cheap Models, Strong Graphs</span>
        <span class="excerpt">Three months running agents in production taught me the model matters less than I thought.</span>
      </a>
    </li>
    <!-- следующие посты добавляются сюда же, тем же паттерном -->
  </ul>
  <a href="/lab" class="all-posts">All posts →</a>
</section>
```
Каждая запись фида — целиком кликабельная строка (дата + заголовок + одна строка сути), без превью-картинок, без кнопок "read more".

### Секция 3 — Футер
```html
<footer>
  <p class="mono">
    <a href="mailto:artem@...">artem@...</a> · <a href="https://github.com/hpnssflw">github.com/hpnssflw</a> · © 2026
  </p>
</footer>
```
Минимально — дублирует контакты из hero внизу страницы, просто чтобы были под рукой после прокрутки фида.

## 3. Отдельная страница поста (шаблон для каждого LAB-поста)

Один HTML-шаблон, переиспользуемый для всех постов:
```html
<article class="post">
  <p class="mono date">AUG 2026</p>
  <h1>Cheap Models, Strong Graphs</h1>
  <p class="subtitle">Three months of running AI agents in production, condensed into three decisions that held up and one that didn't.</p>
  <div class="body">
    <!-- нумерованные инсайты / прозаический текст поста -->
  </div>
  <a href="/lab" class="back">← LAB</a>
</article>
```
Текст первого поста ("Cheap Models, Strong Graphs") уже готов — просто вставляется в `.body`.

## 4. Файловая структура (без React, просто статика)

```
/
├── index.html          (hero + LAB feed + footer)
├── lab/
│   ├── index.html       (полный список постов, если фид на главной — только последние N)
│   └── cheap-models-strong-graphs.html   (первый пост)
├── styles.css           (все токены из раздела 1)
└── assets/
    └── grid-texture.svg (фоновая текстура)
```
Простая статика — никакого билд-шага не нужно, агент может сразу деплоить на Vercel/Netlify/GitHub Pages как статический сайт.

## 5. Не входит в эту итерацию (сознательно)

- FOCUS-секция ("чем занимаюсь сейчас") — отложена, не обсуждена детально, добавить отдельным шагом при желании
- Фото в hero — обсуждалось на раннем этапе, в текущей версии hero не используется, добавить как опциональный элемент, если понадобится
- Агент-куратор контента для LAB — отдельный трек, не часть верстки лендинга
- Тёмная/светлая тема-переключатель — не обсуждалось, сайт по умолчанию только тёмный
