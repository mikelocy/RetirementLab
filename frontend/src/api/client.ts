import axios from 'axios';
import { Scenario, ScenarioCreate, Asset, AssetCreate, SimpleBondSimulationResult } from '../types';

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
