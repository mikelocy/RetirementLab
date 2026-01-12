import axios from 'axios';
import { 
  Scenario, ScenarioCreate, Asset, AssetCreate, SimpleBondSimulationResult, IncomeSource, IncomeSourceCreate,
  Security, SecurityCreate, RSUGrantForecastCreate, RSUGrantForecastRead, RSUGrantDetailsResponse,
  TaxFundingSettings, TaxFundingSettingsCreate, TaxTable, TaxTableCreate
} from '../types';

const api = axios.create({
  baseURL: '/api',
});

export const getScenarios = async (): Promise<Scenario[]> => {
  const response = await api.get<Scenario[]>('/scenarios');
  return response.data;
};

export const createScenario = async (payload: ScenarioCreate): Promise<Scenario> => {
  const response = await api.post<Scenario>('/scenarios', payload);
  return response.data;
};

export const updateScenario = async (id: number, payload: ScenarioCreate): Promise<Scenario> => {
  const response = await api.put<Scenario>(`/scenarios/${id}`, payload);
  return response.data;
};

export const getScenario = async (id: number): Promise<Scenario> => {
  const response = await api.get<Scenario>(`/scenarios/${id}`);
  return response.data;
};

export const deleteScenario = async (id: number): Promise<void> => {
  await api.delete(`/scenarios/${id}`);
};

export const getAssets = async (scenarioId: number): Promise<Asset[]> => {
  const response = await api.get<Asset[]>(`/scenarios/${scenarioId}/assets`);
  return response.data;
};

export const createAsset = async (scenarioId: number, payload: AssetCreate): Promise<Asset> => {
  const response = await api.post<Asset>(`/scenarios/${scenarioId}/assets`, payload);
  return response.data;
};

export const updateAsset = async (assetId: number, payload: AssetCreate): Promise<Asset> => {
  const response = await api.put<Asset>(`/assets/${assetId}`, payload);
  return response.data;
};

export const deleteAsset = async (assetId: number): Promise<void> => {
  await api.delete(`/assets/${assetId}`);
};

export const runSimpleBondSimulation = async (scenarioId: number): Promise<SimpleBondSimulationResult> => {
  const response = await api.get<SimpleBondSimulationResult>(`/scenarios/${scenarioId}/simulate/simple-bond`);
  return response.data;
};

export const getIncomeSources = async (scenarioId: number): Promise<IncomeSource[]> => {
  const response = await api.get<IncomeSource[]>(`/scenarios/${scenarioId}/income_sources`);
  return response.data;
};

export const createIncomeSource = async (scenarioId: number, payload: IncomeSourceCreate): Promise<IncomeSource> => {
  const response = await api.post<IncomeSource>(`/scenarios/${scenarioId}/income_sources`, payload);
  return response.data;
};

export const updateIncomeSource = async (id: number, payload: IncomeSourceCreate): Promise<IncomeSource> => {
  const response = await api.put<IncomeSource>(`/income_sources/${id}`, payload);
  return response.data;
};

export const deleteIncomeSource = async (id: number): Promise<void> => {
  await api.delete(`/income_sources/${id}`);
};

// Security/Ticker endpoints
export const getSecurities = async (): Promise<Security[]> => {
  const response = await api.get<Security[]>('/securities');
  return response.data;
};

export const getSecurity = async (securityId: number): Promise<Security> => {
  const response = await api.get<Security>(`/securities/${securityId}`);
  return response.data;
};

export const getSecurityBySymbol = async (symbol: string): Promise<Security> => {
  const response = await api.get<Security>(`/securities/symbol/${symbol}`);
  return response.data;
};

export const createOrGetSecurity = async (payload: SecurityCreate): Promise<Security> => {
  const response = await api.post<Security>('/securities', payload);
  return response.data;
};

// RSU Grant Forecast endpoints
export const getRSUForecasts = async (scenarioId: number): Promise<RSUGrantForecastRead[]> => {
  const response = await api.get<RSUGrantForecastRead[]>(`/scenarios/${scenarioId}/rsu_forecasts`);
  return response.data;
};

export const createRSUForecast = async (scenarioId: number, payload: RSUGrantForecastCreate): Promise<RSUGrantForecastRead> => {
  const response = await api.post<RSUGrantForecastRead>(`/scenarios/${scenarioId}/rsu_forecasts`, payload);
  return response.data;
};

export const updateRSUForecast = async (forecastId: number, payload: RSUGrantForecastCreate): Promise<RSUGrantForecastRead> => {
  const response = await api.put<RSUGrantForecastRead>(`/rsu_forecasts/${forecastId}`, payload);
  return response.data;
};

export const deleteRSUForecast = async (forecastId: number): Promise<void> => {
  await api.delete(`/rsu_forecasts/${forecastId}`);
};

// RSU Grant Details endpoint
export const getRSUGrantDetails = async (assetId: number): Promise<RSUGrantDetailsResponse> => {
  const response = await api.get<RSUGrantDetailsResponse>(`/assets/${assetId}/rsu_details`);
  return response.data;
};

// Tax Funding Settings endpoints
export const getTaxFundingSettings = async (scenarioId: number): Promise<TaxFundingSettings> => {
  const response = await api.get<TaxFundingSettings>(`/scenarios/${scenarioId}/settings`);
  return response.data;
};

export const updateTaxFundingSettings = async (scenarioId: number, payload: TaxFundingSettingsCreate): Promise<TaxFundingSettings> => {
  const response = await api.put<TaxFundingSettings>(`/scenarios/${scenarioId}/settings`, payload);
  return response.data;
};

export const getTaxTables = async (scenarioId: number): Promise<TaxTable[]> => {
  const response = await api.get<TaxTable[]>(`/scenarios/${scenarioId}/tax-tables`);
  return response.data;
};

export const upsertTaxTable = async (scenarioId: number, jurisdiction: "FED" | "CA", payload: TaxTableCreate): Promise<TaxTable> => {
  const response = await api.put<TaxTable>(`/scenarios/${scenarioId}/tax-tables/${jurisdiction}`, payload);
  return response.data;
};
