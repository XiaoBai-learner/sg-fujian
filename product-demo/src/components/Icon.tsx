const paths = {
  source: 'M4 7c0-3 16-3 16 0s-16 3-16 0m0 0v10c0 3 16 3 16 0V7M4 12c0 3 16 3 16 0',
  model: 'M12 5v5M5 17l7-7 7 7M5 17h0M19 17h0',
  agent: 'M8 8h8m-8 4h5M5 3h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H8l-5 3V5a2 2 0 0 1 2-2',
  arrow: 'M5 12h14m-6-6 6 6-6 6',
  plus: 'M12 5v14M5 12h14',
  file: 'M14 2H5v20h14V7l-5-5m0 0v5h5M8 12h8M8 16h5',
  check: 'm5 12 4 4L19 6',
} as const

export default function Icon({ name }: { name: keyof typeof paths }) {
  return <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d={paths[name]} />{name === 'model' && <><circle cx="12" cy="4" r="2" /><circle cx="5" cy="18" r="2" /><circle cx="19" cy="18" r="2" /></>}</svg>
}
