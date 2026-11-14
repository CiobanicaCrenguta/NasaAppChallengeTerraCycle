// The only place colours, fonts and sizes are defined.
export const colors = {
  ink: '#1F1D1A',
  body: '#3A352F',
  muted: '#5E574F',
  bone: '#F6F3EC', // screen background
  paper: '#FDFBF7', // cards, inputs, tab bar
  sand: '#EDE8DC', // quiet fills, the farmer's own bubble
  line: '#D9D1C0', // separators
  edge: '#1F1D1A', // crisp outline on cards, inputs, buttons
  green: '#2D5A3C',
  greenSoft: '#E2ECE3',
  orange: '#C9772B',
  orangeSoft: '#F5E6D4',
  red: '#B8452E',
  blue: '#3D606E',
  white: '#FFFFFF',
};

export const fonts = {
  title: 'Fraunces_700Bold',
  medium: 'PlusJakartaSans_500Medium',
  semibold: 'PlusJakartaSans_600SemiBold',
  bold: 'PlusJakartaSans_700Bold',
  extrabold: 'PlusJakartaSans_800ExtraBold',
};

export const type = {
  answer: { fontFamily: fonts.title, fontSize: 27, lineHeight: 34, color: colors.ink },
  h1: { fontFamily: fonts.title, fontSize: 31, lineHeight: 38, color: colors.ink },
  h2: { fontFamily: fonts.title, fontSize: 22, color: colors.ink },
  title: { fontFamily: fonts.bold, fontSize: 17, color: colors.ink },
  body: { fontFamily: fonts.medium, fontSize: 16, lineHeight: 23, color: colors.body },
  label: { fontFamily: fonts.semibold, fontSize: 13, color: colors.muted },
  button: { fontFamily: fonts.bold, fontSize: 16 },
} as const;

export const size = { gutter: 20, radius: 18, touch: 48, button: 52 };
