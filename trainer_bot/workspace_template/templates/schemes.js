/*
 * Схемы упражнений: SVG-фигурки сбоку в 1–3 кадрах со стрелками движения.
 *
 * Использование в HTML (out/*.html):
 *   <link rel="stylesheet" href="../templates/schemes.css">
 *   <div class="frames" data-ex="bulg"></div>          ← готовая схема по id
 *   <script src="../templates/schemes.js"></script>
 *   <script>Schemes.add({ myex: [кадр, кадр] })</script>  ← новые схемы, если нужно
 *
 * Готовые id:
 *   bulg, pistol, rdl, calf1, calf2, copen, pallof, deadbug, sideplank, birddog, hollow, bridge, superman, achiso, pulldown, row, pushup, facepull, sofabridge, stepup, dryswim
 *
 * Кадр: { label, vb: [w, h], floor: y, props, guides: [[a, b]], arrows: [[from, to]],
 *         texts: [[x, y, текст, 'm'|'' , 'start'|'middle']], fig | custom }
 *   fig — человек сбоку через person(): head, sh (плечо), hip, kneeW/footW (рабочая нога, оранжевая),
 *         kneeO/footO (вторая нога, серая), elbN/handN (ближняя рука), extraWork/extraFar — доп. отрезки.
 *   custom — произвольная фигурка: segs([[a, b, 'ink'|'work'|'far'|'band'], ...], headXY).
 *   Классы линий: ink — корпус, work — работающее звено, far — дальние конечности, band — резинка,
 *   guide — пунктир-ориентир, move — стрелки. Опоры: chair(x1, x2, seatY, floorY, backX), step, doorTop, db(x, y).
 * Берите похожую готовую схему за основу и двигайте суставы: так стиль остаётся единым.
 */
(function () {
  let uid = 0;
  const ln = (a, b, cls) => `<line class="${cls}" x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}"/>`;

  // Фигурка сбоку: дальняя нога, корпус, рабочая нога, ближняя рука, голова
  function person(j) {
    let s = '';
    if (j.kneeO) s += ln(j.hip, j.kneeO, 'far') + ln(j.kneeO, j.footO, 'far');
    if (j.extraFar) j.extraFar.forEach(e => s += ln(e[0], e[1], 'far'));
    s += ln(j.hip, j.sh, 'ink') + ln(j.sh, j.head, 'ink');
    if (j.kneeW) s += ln(j.hip, j.kneeW, 'work') + ln(j.kneeW, j.footW, 'work');
    if (j.extraWork) j.extraWork.forEach(e => s += ln(e[0], e[1], 'work'));
    if (j.elbN) s += ln(j.sh, j.elbN, 'ink') + ln(j.elbN, j.handN, 'ink');
    s += `<circle class="head" cx="${j.head[0]}" cy="${j.head[1]}" r="9"/>`;
    return s;
  }
  function arrow(a, b, id) { return `<line class="move" x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" marker-end="url(#${id})"/>`; }
  function svg(fr) {
    const id = 'mk' + (uid++);
    const [w, h] = fr.vb;
    let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${fr.label}"><defs><marker id="${id}" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse"><path class="mh" d="M0,0 L10,5 L0,10 z"/></marker></defs>`;
    if (fr.floor) s += ln([4, fr.floor], [w - 4, fr.floor], 'floor');
    s += fr.props || '';
    (fr.guides || []).forEach(g => s += ln(g[0], g[1], 'guide'));
    s += fr.custom ? fr.custom : person(fr.fig);
    (fr.arrows || []).forEach(a => s += arrow(a[0], a[1], id));
    (fr.texts || []).forEach(t => s += `<text x="${t[0]}" y="${t[1]}" class="${t[3] || ''}" text-anchor="${t[4] || 'start'}">${t[2]}</text>`);
    return s + '</svg>';
  }

  const chair = (x1, x2, seat, floor, backX) =>
    `<path class="prop" d="M${x1} ${seat} H${x2} M${x1 + 2} ${seat} V${floor} M${x2 - 2} ${seat} V${floor} M${backX} ${seat} V${seat - 38}"/>`;
  const step = `<rect class="propfill" x="70" y="168" width="50" height="22" rx="2"/><line class="prop" x1="123" y1="10" x2="123" y2="190"/><text x="126" y="24">стена</text>`;

  const EX = {
    bulg: [
      { label: 'Старт', vb: [150, 170], floor: 156, props: chair(20, 56, 118, 156, 22),
        fig: { head: [88, 24], sh: [87, 37], hip: [84, 81], kneeW: [96, 117], footW: [100, 155], kneeO: [80, 119], footO: [42, 114],
          extraWork: [[[100, 155], [111, 155]]], extraFar: [[[42, 114], [31, 117]]], elbN: [89, 62], handN: [90, 85] } },
      { label: 'Низ: колено 90°', vb: [150, 170], floor: 156, props: chair(20, 56, 118, 156, 22),
        fig: { head: [77, 61], sh: [76, 74], hip: [70, 118], kneeW: [104, 118], footW: [100, 155], kneeO: [54, 150], footO: [42, 114],
          extraWork: [[[100, 155], [111, 155]]], extraFar: [[[42, 114], [31, 117]]], elbN: [78, 99], handN: [80, 121] },
        arrows: [[[128, 70], [128, 108]]], texts: [[124, 64, 'вниз', 'm', 'middle']] }
    ],
    pistol: [
      { label: 'Старт: руки вперёд', vb: [160, 170], floor: 156, props: chair(26, 62, 119, 156, 28),
        fig: { head: [81, 21], sh: [81, 34], hip: [80, 79], kneeW: [80, 117], footW: [80, 155], kneeO: [95, 113], footO: [108, 146],
          extraWork: [[[80, 155], [90, 155]]], elbN: [105, 36], handN: [129, 38] } },
      { label: 'Низ: коснуться стула', vb: [160, 170], floor: 156, props: chair(26, 62, 119, 156, 28),
        fig: { head: [86, 64], sh: [80, 76], hip: [58, 116], kneeW: [96, 120], footW: [80, 155], kneeO: [95, 110], footO: [130, 104],
          extraWork: [[[80, 155], [90, 155]]], elbN: [104, 77], handN: [128, 77] },
        arrows: [[[46, 66], [46, 100]]], texts: [[46, 60, '3 с', 'm', 'middle']] }
    ],
    rdl: [
      { label: 'Старт', vb: [160, 170], floor: 156,
        fig: { head: [85, 21], sh: [85, 34], hip: [85, 79], kneeW: [86, 117], footW: [85, 155], kneeO: [80, 116], footO: [72, 150],
          extraWork: [[[85, 155], [95, 155]]], extraFar: [[[72, 150], [81, 151]]], elbN: [87, 60], handN: [88, 84] } },
      { label: 'Наклон: одна линия', vb: [160, 170], floor: 156,
        guides: [[[140, 72], [6, 91]]],
        fig: { head: [137, 73], sh: [124, 76], hip: [82, 82], kneeW: [89, 118], footW: [85, 155], kneeO: [46, 86], footO: [9, 90],
          extraWork: [[[85, 155], [95, 155]]], extraFar: [[[9, 90], [8, 99]]], elbN: [124, 100], handN: [124, 124] },
        arrows: [[[112, 32], [136, 54]]], texts: [[108, 28, 'от бедра', 'm', 'middle']] }
    ],
    calf1: [
      { label: 'Низ: пятка ниже ступеньки', vb: [160, 200], floor: 190, props: step,
        guides: [[[30, 168], [70, 168]]],
        fig: { head: [72, 31], sh: [72, 44], hip: [72, 89], kneeW: [71, 127], footW: [70, 165], kneeO: [70, 126], footO: [40, 142],
          extraWork: [[[66, 174], [86, 168]]], elbN: [96, 56], handN: [120, 52] },
        arrows: [[[30, 110], [30, 140]]], texts: [[30, 104, 'вниз 3 с', 'm', 'middle']] },
      { label: 'Верх: пауза 1 с', vb: [160, 200], floor: 190, props: step,
        fig: { head: [75, 14], sh: [75, 27], hip: [75, 72], kneeW: [75, 110], footW: [75, 148], kneeO: [73, 109], footO: [43, 125],
          extraWork: [[[72, 151], [86, 168]]], elbN: [98, 40], handN: [121, 36] },
        arrows: [[[30, 170], [30, 140]]], texts: [[30, 182, 'вверх 1 с', 'm', 'middle']] }
    ],
    calf2: [
      { label: 'Низ', vb: [160, 200], floor: 190, props: step,
        guides: [[[30, 168], [70, 168]]],
        fig: { head: [71, 39], sh: [70, 52], hip: [66, 97], kneeW: [84, 130], footW: [70, 165], kneeO: [64, 134], footO: [34, 148],
          extraWork: [[[66, 174], [86, 168]]], elbN: [94, 62], handN: [120, 56] },
        texts: [[92, 134, '~30°', 'm']] },
      { label: 'Верх: колено так же согнуто', vb: [160, 200], floor: 190, props: step,
        fig: { head: [76, 22], sh: [75, 35], hip: [71, 80], kneeW: [89, 113], footW: [75, 148], kneeO: [69, 117], footO: [39, 131],
          extraWork: [[[72, 151], [86, 168]]], elbN: [98, 46], handN: [121, 40] },
        arrows: [[[30, 170], [30, 140]]], texts: [[97, 117, '~30°', 'm'], [30, 182, 'пятка вверх', 'm', 'middle']] }
    ],
    copen: [
      { label: 'Держать 15 с, тело — прямая линия', vb: [200, 150], floor: 140,
        props: `<path class="prop" d="M116 103 H170 M118 103 V140 M168 103 V140 M168 103 V66"/>`,
        guides: [[[22, 115], [168, 96]]],
        fig: { head: [28, 114], sh: [42, 112], hip: [86, 104], kneeW: [124, 100], footW: [160, 98], kneeO: [110, 130], footO: [138, 123],
          extraFar: [[[42, 112], [40, 138]], [[40, 138], [58, 138]]], elbN: [62, 94], handN: [84, 99] },
        arrows: [[[86, 136], [86, 116]]], texts: [[92, 134, 'таз вверх', 'm'], [143, 92, 'колено на стуле', '', 'middle']] }
    ],
    pallof: [
      { label: 'Старт: руки у груди (вид сверху)', vb: [170, 150],
        custom: pallof(false) },
      { label: 'Жим вперёд, пауза 2 с', vb: [170, 150],
        custom: pallof(true),
        arrows: [[[150, 72], [150, 108]]], texts: [[150, 120, 'вперёд', 'm', 'middle']] }
    ]
  };

  function pallof(out) {
    const hand = out ? [103, 108] : [103, 84];
    let s = `<rect class="propfill" x="4" y="50" width="12" height="40" rx="2"/><text x="10" y="102" text-anchor="middle">дверь</text>`;
    s += `<line class="band" x1="16" y1="68" x2="${hand[0]}" y2="${hand[1]}"/>`;
    if (out) {
      s += ln([78, 60], hand, 'ink') + ln([128, 60], hand, 'ink');
    } else {
      s += ln([78, 60], [82, 82], 'ink') + ln([82, 82], hand, 'ink') + ln([128, 60], [124, 82], 'ink') + ln([124, 82], hand, 'ink');
    }
    s += `<line class="ink" x1="76" y1="60" x2="130" y2="60" style="stroke-width:7"/>`;
    s += `<circle class="head" cx="103" cy="58" r="11"/>`;
    s += `<text x="103" y="30" text-anchor="middle">спина</text>`;
    s += `<text x="50" y="${out ? 102 : 88}" class="m" text-anchor="middle">не поворачивайся</text>`;
    return s;
  }

  // Фигурка из произвольных отрезков [a, b, класс] — для положений лёжа и на четвереньках
  function segs(list, head) {
    return list.map(x => ln(x[0], x[1], x[2])).join('') + `<circle class="head" cx="${head[0]}" cy="${head[1]}" r="9"/>`;
  }

  Object.assign(EX, {
    deadbug: [
      { label: 'Старт: руки вверх, колени 90°', vb: [195, 118], floor: 100,
        custom: segs([
          [[64, 92], [108, 92], 'ink'], [[64, 92], [50, 91], 'ink'],
          [[108, 92], [108, 54], 'ink'], [[108, 54], [146, 54], 'ink'],
          [[64, 92], [64, 66], 'ink'], [[64, 66], [64, 42], 'ink']], [50, 91]),
        texts: [[86, 113, 'поясница прижата', 'm', 'middle']] },
      { label: 'Опустить разноимённые руку и ногу', vb: [195, 118], floor: 100,
        custom: segs([
          [[108, 92], [108, 54], 'far'], [[108, 54], [146, 54], 'far'],
          [[64, 92], [64, 66], 'far'], [[64, 66], [64, 42], 'far'],
          [[64, 92], [108, 92], 'ink'], [[64, 92], [50, 91], 'ink'],
          [[108, 92], [145, 86], 'work'], [[145, 86], [182, 84], 'work'],
          [[64, 92], [40, 80], 'work'], [[40, 80], [16, 82], 'work']], [50, 91]),
        arrows: [[[56, 38], [26, 66]], [[156, 50], [180, 72]]],
        texts: [[86, 113, 'поясница прижата', 'm', 'middle']] }
    ],
    sideplank: [
      { label: 'Держать 30 с на каждую сторону', vb: [195, 118], floor: 100,
        custom: segs([
          [[30, 100], [50, 100], 'far'], [[32, 74], [30, 100], 'far'],
          [[32, 74], [76, 83], 'work'], [[32, 74], [19, 71], 'ink'],
          [[76, 83], [113, 91], 'ink'], [[113, 91], [150, 99], 'ink'],
          [[32, 74], [32, 50], 'ink'], [[32, 50], [32, 26], 'ink']], [19, 71]),
        guides: [[[12, 66], [176, 101]]],
        arrows: [[[90, 116], [90, 96]]], texts: [[98, 114, 'таз не провисает', 'm']] }
    ],
    birddog: [
      { label: 'Старт: на четвереньках', vb: [195, 122], floor: 110,
        custom: segs([
          [[60, 60], [105, 72], 'ink'], [[60, 60], [48, 56], 'ink'],
          [[60, 60], [60, 85], 'ink'], [[60, 85], [60, 110], 'ink'],
          [[105, 72], [105, 110], 'ink'], [[105, 110], [143, 110], 'ink']], [48, 56]) },
      { label: 'Рука вперёд, нога назад, пауза 2 с', vb: [195, 122], floor: 110,
        custom: segs([
          [[60, 60], [60, 85], 'far'], [[60, 85], [60, 110], 'far'],
          [[60, 60], [105, 72], 'ink'], [[60, 60], [48, 56], 'ink'],
          [[105, 72], [105, 110], 'ink'], [[105, 110], [143, 110], 'ink'],
          [[60, 60], [35, 58], 'work'], [[35, 58], [9, 56], 'work'],
          [[105, 72], [142, 68], 'work'], [[142, 68], [180, 64], 'work']], [48, 56]),
        guides: [[[6, 46], [184, 54]]], texts: [[95, 36, 'одна линия, таз ровно', 'm', 'middle']] }
    ],
    hollow: [
      { label: 'Лёжа на спине, держать 20 с', vb: [195, 104], floor: 90,
        custom: segs([
          [[100, 86], [57, 76], 'work'], [[57, 76], [45, 70], 'ink'],
          [[57, 76], [32, 70], 'ink'], [[32, 70], [8, 64], 'ink'],
          [[100, 86], [137, 80], 'ink'], [[137, 80], [174, 74], 'ink']], [45, 70]),
        arrows: [[[96, 50], [96, 74]]], texts: [[96, 44, 'поясница в пол', 'm', 'middle'], [100, 101, 'на спине', '', 'middle']] }
    ],
    bridge: [
      { label: 'Старт: стопы у таза', vb: [170, 104], floor: 92,
        custom: segs([
          [[34, 89], [84, 90], 'far'],
          [[34, 86], [78, 86], 'ink'], [[34, 86], [20, 83], 'ink'],
          [[78, 86], [103, 57], 'work'], [[103, 57], [122, 90], 'work']], [20, 83]),
        arrows: [[[74, 78], [74, 54]]], texts: [[74, 48, 'таз вверх', 'm', 'middle']] },
      { label: 'Верх: сжать ягодицы 1–2 с', vb: [170, 104], floor: 92,
        custom: segs([
          [[34, 89], [84, 90], 'far'],
          [[34, 86], [76, 69], 'ink'], [[34, 86], [20, 83], 'ink'],
          [[76, 69], [111, 54], 'work'], [[111, 54], [122, 90], 'work']], [20, 83]),
        guides: [[[30, 78], [112, 44]]], texts: [[64, 50, 'прямая линия', 'm', 'middle']] }
    ],
    superman: [
      { label: 'Лёжа на животе, пауза 2 с', vb: [195, 100], floor: 80,
        custom: segs([
          [[100, 76], [58, 68], 'work'], [[58, 68], [45, 63], 'ink'],
          [[58, 68], [33, 62], 'ink'], [[33, 62], [8, 57], 'ink'],
          [[100, 76], [137, 72], 'ink'], [[137, 72], [174, 66], 'ink']], [45, 63]),
        arrows: [[[16, 46], [16, 30]], [[170, 56], [170, 40]]],
        texts: [[100, 94, 'на животе, взгляд в пол', '', 'middle'], [93, 50, '5–10 см', 'm', 'middle']] }
    ]
  });

  const db = (x, y) => `<rect class="db" x="${x - 8}" y="${y - 3}" width="16" height="6" rx="2"/>`;
  const doorTop = `<line class="prop" x1="150" y1="6" x2="150" y2="156"/><circle class="propfill" cx="148" cy="12" r="3"/>`;
  const standLegs = [[[80, 79], [80, 117], 'ink'], [[80, 117], [80, 155], 'ink'], [[80, 155], [90, 155], 'ink'], [[80, 79], [76, 35], 'ink'], [[76, 35], [75, 22], 'ink']];
  const bentBody = [[[70, 80], [72, 117], 'ink'], [[72, 117], [70, 155], 'ink'], [[70, 155], [80, 155], 'ink'], [[70, 80], [114, 74], 'ink'], [[114, 74], [127, 72], 'ink']];
  const swimDoor = `<line class="prop" x1="174" y1="20" x2="174" y2="156"/><circle class="propfill" cx="172" cy="90" r="3"/>`;

  Object.assign(EX, {
    achiso: [
      { label: 'Полуподъём на полу, держать 45 с', vb: [160, 200], floor: 190,
        props: `<line class="prop" x1="123" y1="10" x2="123" y2="190"/><text x="126" y="24">стена</text>`,
        custom: segs([
          [[79, 102], [75, 139], 'far'], [[75, 139], [45, 155], 'far'],
          [[79, 102], [79, 57], 'ink'], [[79, 57], [79, 44], 'ink'],
          [[79, 102], [79, 140], 'work'], [[79, 140], [79, 178], 'work'], [[76, 182], [92, 190], 'work'],
          [[79, 57], [101, 70], 'ink'], [[101, 70], [121, 66], 'ink']], [79, 44]),
        texts: [[36, 176, 'пятка на полпути', 'm', 'middle']] }
    ],
    pulldown: [
      { label: 'Старт: руки к двери', vb: [170, 170], floor: 156, props: doorTop,
        custom: segs(standLegs.concat([
          [[76, 35], [98, 22], 'work'], [[98, 22], [120, 14], 'work'], [[120, 14], [148, 12], 'band']]), [75, 22]) },
      { label: 'Локти к рёбрам', vb: [170, 170], floor: 156, props: doorTop,
        custom: segs(standLegs.concat([
          [[90, 42], [148, 12], 'band'], [[76, 35], [72, 60], 'work'], [[72, 60], [90, 42], 'work']]), [75, 22]),
        arrows: [[[118, 34], [104, 56]]] }
    ],
    row: [
      { label: 'Старт: рука прямая', vb: [170, 170], floor: 156, props: chair(108, 150, 112, 156, 148),
        custom: segs([
          [[60, 80], [70, 117], 'far'], [[70, 117], [72, 155], 'far'], [[72, 155], [82, 155], 'far'],
          [[60, 80], [52, 117], 'ink'], [[52, 117], [52, 155], 'ink'], [[52, 155], [62, 155], 'ink'],
          [[60, 80], [104, 72], 'ink'], [[104, 72], [117, 68], 'ink'],
          [[104, 72], [112, 92], 'far'], [[112, 92], [118, 110], 'far'],
          [[104, 72], [102, 98], 'work'], [[102, 98], [101, 122], 'work']], [117, 68]) + db(101, 124) },
      { label: 'Локоть к бедру, пауза 1 с', vb: [170, 170], floor: 156, props: chair(108, 150, 112, 156, 148),
        custom: segs([
          [[60, 80], [70, 117], 'far'], [[70, 117], [72, 155], 'far'], [[72, 155], [82, 155], 'far'],
          [[60, 80], [52, 117], 'ink'], [[52, 117], [52, 155], 'ink'], [[52, 155], [62, 155], 'ink'],
          [[60, 80], [104, 72], 'ink'], [[104, 72], [117, 68], 'ink'],
          [[104, 72], [112, 92], 'far'], [[112, 92], [118, 110], 'far'],
          [[104, 72], [82, 62], 'work'], [[82, 62], [84, 86], 'work']], [117, 68]) + db(84, 88),
        arrows: [[[100, 118], [92, 96]]], texts: [[80, 40, 'локоть назад', 'm', 'middle']] }
    ],
    pushup: [
      { label: 'Верх: тело — прямая', vb: [195, 112], floor: 100,
        custom: segs([
          [[60, 52], [102, 69], 'ink'], [[102, 69], [137, 82], 'ink'], [[137, 82], [172, 97], 'ink'],
          [[60, 52], [48, 48], 'ink'],
          [[60, 52], [60, 77], 'work'], [[60, 77], [60, 100], 'work']], [48, 48]),
        arrows: [[[26, 58], [26, 86]]], texts: [[26, 52, 'вниз', 'm', 'middle']] },
      { label: 'Низ: грудь у пола', vb: [195, 112], floor: 100,
        custom: segs([
          [[64, 84], [109, 89], 'ink'], [[109, 89], [146, 94], 'ink'], [[146, 94], [184, 98], 'ink'],
          [[64, 84], [51, 82], 'ink'],
          [[64, 84], [88, 92], 'work'], [[88, 92], [60, 100], 'work']], [51, 82]),
        texts: [[120, 70, 'локти назад, ~45°', 'm', 'middle']] }
    ],
    facepull: [
      { label: 'Старт: руки прямые (вид сверху)', vb: [170, 150],
        custom: `<rect class="propfill" x="60" y="2" width="50" height="6" rx="1"/><text x="118" y="10">дверь</text>`
          + segs([[[85, 8], [85, 62], 'band'], [[60, 110], [82, 62], 'work'], [[110, 110], [88, 62], 'work'], [[58, 110], [112, 110], 'ink']], [85, 108]) },
      { label: 'Локти в стороны, кисти к вискам', vb: [170, 150],
        custom: `<rect class="propfill" x="60" y="2" width="50" height="6" rx="1"/><text x="118" y="10">дверь</text>`
          + segs([[[85, 8], [58, 86], 'band'], [[85, 8], [112, 86], 'band'],
            [[60, 110], [36, 100], 'work'], [[36, 100], [58, 86], 'work'], [[110, 110], [134, 100], 'work'], [[134, 100], [112, 86], 'work'],
            [[58, 110], [112, 110], 'ink']], [85, 108]),
        texts: [[85, 140, 'лопатки сведены', 'm', 'middle']] }
    ],
    sofabridge: [
      { label: 'Низ: таз опущен', vb: [170, 172], floor: 156,
        props: `<path class="propfill" d="M6 92 H52 V156 H6 Z"/><path class="propfill" d="M6 92 V58 H20 V92 Z"/>`,
        custom: segs([
          [[74, 123], [108, 106], 'far'], [[108, 106], [142, 89], 'far'],
          [[46, 88], [74, 123], 'ink'], [[46, 88], [34, 84], 'ink'],
          [[74, 123], [112, 117], 'work'], [[112, 117], [124, 153], 'work'], [[124, 153], [134, 153], 'work']], [34, 84]),
        arrows: [[[80, 152], [80, 132]]], texts: [[80, 168, 'таз вверх', 'm', 'middle']] },
      { label: 'Верх: плечи, таз, колено в линию', vb: [170, 172], floor: 156,
        props: `<path class="propfill" d="M6 92 H52 V156 H6 Z"/><path class="propfill" d="M6 92 V58 H20 V92 Z"/>`,
        guides: [[[36, 78], [132, 110]]],
        custom: segs([
          [[88, 100], [118, 78], 'far'], [[118, 78], [148, 56], 'far'],
          [[46, 88], [88, 100], 'ink'], [[46, 88], [34, 84], 'ink'],
          [[88, 100], [124, 113], 'work'], [[124, 113], [124, 153], 'work'], [[124, 153], [134, 153], 'work']], [34, 84]) }
    ],
    stepup: [
      { label: 'Старт: стопа на стуле', vb: [170, 210], floor: 196,
        props: `<rect class="propfill" x="88" y="160" width="52" height="36" rx="2"/>`,
        custom: segs([
          [[70, 122], [64, 159], 'far'], [[64, 159], [60, 195], 'far'], [[60, 195], [70, 195], 'far'],
          [[70, 122], [76, 78], 'ink'], [[76, 78], [78, 65], 'ink'],
          [[70, 122], [108, 122], 'work'], [[108, 122], [100, 159], 'work'], [[100, 159], [110, 159], 'work'],
          [[76, 78], [77, 102], 'ink'], [[77, 102], [78, 126], 'ink']], [78, 65]),
        arrows: [[[36, 170], [36, 124]]], texts: [[36, 186, 'толкай пяткой', 'm', 'middle']] },
      { label: 'Верх: выпрямиться полностью', vb: [170, 210], floor: 196,
        props: `<rect class="propfill" x="88" y="160" width="52" height="36" rx="2"/>`,
        custom: segs([
          [[104, 83], [110, 119], 'far'], [[110, 119], [100, 150], 'far'],
          [[104, 83], [104, 38], 'ink'], [[104, 38], [104, 25], 'ink'],
          [[104, 83], [104, 121], 'work'], [[104, 121], [104, 159], 'work'], [[104, 159], [114, 159], 'work'],
          [[104, 38], [105, 62], 'ink'], [[105, 62], [106, 86], 'ink']], [104, 25]) }
    ],
    dryswim: [
      { label: 'Захват впереди', vb: [180, 170], floor: 156, props: swimDoor,
        custom: segs(bentBody.concat([[[156, 98], [172, 90], 'band'], [[114, 74], [134, 90], 'work'], [[134, 90], [156, 98], 'work']]), [127, 72]) },
      { label: 'Высокий локоть', vb: [180, 170], floor: 156, props: swimDoor,
        custom: segs(bentBody.concat([[[134, 110], [172, 90], 'band'], [[114, 74], [136, 84], 'work'], [[136, 84], [134, 110], 'work']]), [127, 72]),
        texts: [[138, 132, 'локоть выше кисти', 'm', 'middle']] },
      { label: 'Толчок до бедра', vb: [180, 170], floor: 156, props: swimDoor,
        custom: segs(bentBody.concat([[[78, 104], [172, 90], 'band'], [[114, 74], [96, 92], 'work'], [[96, 92], [78, 104], 'work']]), [127, 72]) }
    ]
  });

  function render(root) {
    (root || document).querySelectorAll('.frames[data-ex]').forEach(el => {
      const frames = EX[el.dataset.ex];
      if (!frames) {
        el.innerHTML = `<p class="why">Нет схемы «${el.dataset.ex}»: добавь её через Schemes.add()</p>`;
        return;
      }
      el.innerHTML = frames.map(fr => `<figure class="frame" style="margin:0">${svg(fr)}<figcaption>${fr.label}</figcaption></figure>`)
        .join('<span class="between" aria-hidden="true">→</span>');
    });
  }

  window.Schemes = {
    EX, render, svg, person, segs, ln, chair, db, step, doorTop, swimDoor, standLegs, bentBody,
    add(extra) { Object.assign(EX, extra); },
  };
  // Отрисовка после всех скриптов страницы, чтобы Schemes.add() успел добавить новые схемы.
  document.addEventListener('DOMContentLoaded', () => render());
})();
