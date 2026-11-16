const paths = {
  source: 'M4 7c0-3 16-3 16 0s-16 3-16 0m0 0v10c0 3 16 3 16 0V7M4 12c0 3 16 3 16 0',
  model: 'M12 5v5M5 17l7-7 7 7M5 17h0M19 17h0',
  agent: 'M8 8h8m-8 4h5M5 3h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H8l-5 3V5a2 2 0 0 1 2-2',
  arrow: 'M5 12h14m-6-6 6 6-6 6',
  plus: 'M12 5v14M5 12h14',
  file: 'M14 2H5v20h14V7l-5-5m0 0v5h5M8 12h8M8 16h5',
  check: 'm5 12 4 4L19 6',
  panel: 'M9 3v18M4 3h16a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1',
  folder: 'M3 7V5a1 1 0 0 1 1-1h5l2 3h9a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7h18',
  search: 'm16 16 5 5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  chevron: 'm9 5 7 7-7 7',
  up: 'M12 19V5m-6 6 6-6 6 6',
  close: 'm6 6 12 12M6 18 18 6',
  help: 'M9 9a3 3 0 0 1 6 0c0 2-3 2-3 4m0 3h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
  trace: 'M3 17V9a6 6 0 0 1 6-6h7M8 21h7a6 6 0 0 0 6-6V7M3 13h9l6-6M12 13v8M14 7h4v4',
  upload: 'M12 16V3m-4 4 4-4 4 4M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5',
  spark: 'm12 3 2.3 6.7L21 12l-6.7 2.3L12 21l-2.3-6.7L3 12l6.7-2.3L12 3M20 2v4m-2-2h4',
} as const

export default function Icon({ name }: { name: keyof typeof paths }) {
  return <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d={paths[name]} />{name === 'model' && <><circle cx="12" cy="4" r="2" /><circle cx="5" cy="18" r="2" /><circle cx="19" cy="18" r="2" /></>}</svg>
}
