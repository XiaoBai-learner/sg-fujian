const paths = {
  minus: 'M5 12h14',
  down: 'm6 9 6 6 6-6',
  settings: 'M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1 1-3M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  grid: 'M3 3h7v7H3V3m11 0h7v7h-7V3M3 14h7v7H3v-7m11 0h7v7h-7v-7',
  link: 'M10 7l2-2a5 5 0 0 1 7 7l-3 3M14 17l-2 2a5 5 0 0 1-7-7l3-3m1 6 6-6',
  fit: 'M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M8 8h8v8H8V8',
  collapse: 'M4 8h16M4 16h16m4-13-4 4-4-4m8 18-4-4-4 4',

  refresh: 'M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-2l2 3M4 16l2 3a7 7 0 0 0 12-2',
  edit: 'm15 4 5 5M4 20l4-1L21 6l-4-4L4 15v5',
  image: 'M3 3h18v18H3V3m0 14 6-6 5 5 3-3 4 4M16 7h.01',
  source: 'M4 7c0-3 16-3 16 0s-16 3-16 0m0 0v10c0 3 16 3 16 0V7M4 12c0 3 16 3 16 0',
  model: 'M12 5v5M5 17l7-7 7 7',
  agent: 'M8 8h8m-8 4h5M5 3h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H8l-5 3V5a2 2 0 0 1 2-2',
  arrow: 'M5 12h14m-6-6 6 6-6 6',
  plus: 'M12 5v14M5 12h14',
  file: 'M14 3H5v18h14V8l-5-5m0 0v5h5M8 12h8M8 16h5',
  check: 'm5 12 4 4L19 6',
  panel: 'M9 3v18M4 3h16a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1',
  folder: 'M3 7V5a1 1 0 0 1 1-1h5l2 3h9a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7h18',
  search: 'm16 16 5 5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  chevron: 'm9 5 7 7-7 7',
  up: 'M12 19V5m-6 6 6-6 6 6',
  close: 'm6 6 12 12M6 18 18 6',
  trace: 'M3 17V9a6 6 0 0 1 6-6h7M8 21h7a6 6 0 0 0 6-6V7M3 13h9l6-6M12 13v8M14 7h4v4',
  upload: 'M12 16V3m-4 4 4-4 4 4M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5',
  spark: 'm12 3 2.3 6.7L21 12l-6.7 2.3L12 21l-2.3-6.7L3 12l6.7-2.3L12 3',
  code: 'm8 7-5 5 5 5m8-10 5 5-5 5M14 4l-4 16',
  shield: 'm12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3m-4 9 3 3 5-6',
  clock: 'M12 6v6l4 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
  info: 'M12 11v6m0-10h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
  play: 'm9 5 11 7-11 7V5',
  expand: 'M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5',
  logout: 'M9 3H4v18h5m5-14 5 5-5 5M8 12h11',
} as const
export type IconName = keyof typeof paths
export default function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d={paths[name]} />{name === 'model' && <><circle cx="12" cy="4" r="2" /><circle cx="5" cy="18" r="2" /><circle cx="19" cy="18" r="2" /></>}
  </svg>
}
