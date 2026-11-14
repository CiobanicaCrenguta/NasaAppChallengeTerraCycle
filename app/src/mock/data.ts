// SAMPLE DATA for building the interface. Every number here is made up
// and must be replaced by the real backend (NASA data + rotation engine).
import type { Health, Polygon } from '../types';

export const ME = { name: 'Mariana', region: 'Dolj' };

export type MockField = { id: string; name: string; cropId: string; ha: number; health: Health; history: { year: number; cropId: string }[]; geometry: Polygon };

export const FIELDS: MockField[] = [
  { id: 'vm', name: 'Valea Mare', cropId: 'sunflower', ha: 48.5, health: 'weak_spot',
    history: [{ year: 2024, cropId: 'corn' }, { year: 2025, cropId: 'wheat' }, { year: 2026, cropId: 'sunflower' }],
    geometry: { type: 'Polygon', coordinates: [[[23.9550, 44.2440], [23.9620, 44.2450], [23.9640, 44.2400], [23.9560, 44.2390], [23.9550, 44.2440]]] } },
  { id: 'dv', name: 'Dealul Viei', cropId: 'corn', ha: 32.0, health: 'below_usual',
    history: [{ year: 2024, cropId: 'sunflower' }, { year: 2025, cropId: 'corn' }, { year: 2026, cropId: 'corn' }],
    geometry: { type: 'Polygon', coordinates: [[[23.9665, 44.2452], [23.9735, 44.2456], [23.9728, 44.2412], [23.9658, 44.2408], [23.9665, 44.2452]]] } },
  { id: 'lj', name: 'Lunca Jiului', cropId: 'wheat', ha: 64.2, health: 'good',
    history: [{ year: 2024, cropId: 'corn' }, { year: 2025, cropId: 'rapeseed' }, { year: 2026, cropId: 'wheat' }],
    geometry: { type: 'Polygon', coordinates: [[[23.9530, 44.2383], [23.9600, 44.2379], [23.9660, 44.2386], [23.9675, 44.2340], [23.9520, 44.2336], [23.9530, 44.2383]]] } },
  { id: 'pv', name: 'Pădurea Veche', cropId: 'rapeseed', ha: 19.8, health: 'good',
    history: [{ year: 2024, cropId: 'sunflower' }, { year: 2025, cropId: 'wheat' }, { year: 2026, cropId: 'rapeseed' }],
    geometry: { type: 'Polygon', coordinates: [[[23.9695, 44.2396], [23.9765, 44.2402], [23.9758, 44.2365], [23.9688, 44.2362], [23.9695, 44.2396]]] } },
];

/** water / soil / income are 1 (low) to 3 (high). minGap = years before the crop may return. */
export type Crop = { id: string; en: string; ro: string; family: string; water: number; soil: number; income: number; nfix?: boolean; early?: boolean; minGap?: number };
export const CROPS: Crop[] = [
  { id: 'barley', en: 'Winter barley', ro: 'Orz de toamnă', family: 'cereal', water: 1, soil: 1, income: 1, early: true },
  { id: 'wheat', en: 'Winter wheat', ro: 'Grâu de toamnă', family: 'cereal', water: 2, soil: 1, income: 2, early: true },
  { id: 'rapeseed', en: 'Rapeseed', ro: 'Rapiță', family: 'brassica', water: 2, soil: 2, income: 3, early: true, minGap: 3 },
  { id: 'corn', en: 'Corn', ro: 'Porumb', family: 'maize', water: 3, soil: 1, income: 3 },
  { id: 'sunflower', en: 'Sunflower', ro: 'Floarea-soarelui', family: 'aster', water: 2, soil: 1, income: 3, minGap: 4 },
  { id: 'peas', en: 'Peas', ro: 'Mazăre', family: 'legume', water: 1, soil: 3, income: 1, nfix: true, early: true, minGap: 4 },
  { id: 'soy', en: 'Soybean', ro: 'Soia', family: 'legume', water: 3, soil: 3, income: 2, nfix: true, minGap: 3 },
  { id: 'alfalfa', en: 'Alfalfa', ro: 'Lucernă', family: 'legume', water: 2, soil: 3, income: 1, nfix: true },
  { id: 'sorghum', en: 'Sorghum', ro: 'Sorg', family: 'sorghum', water: 1, soil: 1, income: 1 },
];

export const JULY_RAIN = { years: [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026], mm: [41, 35, 38, 29, 33, 22, 27, 15, 19, 8] };
export const YEARS = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
export const YEAR_RAIN = [612, 580, 640, 540, 575, 498, 530, 455, 470, 402];
export const SUMMER_TEMP = [22.1, 22.4, 22.9, 22.6, 23.2, 23.8, 23.5, 24.3, 24.1, 24.9];
export const SOIL_WATER = { values: [0.31, 0.3, 0.27, 0.22, 0.15, 0.14, 0.17], usual: [0.31, 0.3, 0.28, 0.25, 0.21, 0.2, 0.22] };
export const HEALTH_SERIES = { values: [0.22, 0.42, 0.62, 0.66, 0.5, 0.42, 0.38], usual: [0.22, 0.42, 0.64, 0.72, 0.68, 0.56, 0.42] };
