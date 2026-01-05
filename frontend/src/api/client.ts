import axios from 'axios';
import { ScenarioSummary, ScenarioDetail, ValidationResult, MaterialInfo } from './models';

// Create helper instance
export const apiClient = axios.create({
    baseURL: '/api', // Vite proxy will handle this
    headers: {
        'Content-Type': 'application/json',
    },
});

export const ScenariosService = {
    list: async (): Promise<ScenarioSummary[]> => {
        const response = await apiClient.get<ScenarioSummary[]>('/scenarios/');
        return response.data;
    },

    get: async (filename: string): Promise<ScenarioDetail> => {
        const response = await apiClient.get<ScenarioDetail>(`/scenarios/${filename}`);
        return response.data;
    },

    validate: async (yamlContent: string): Promise<ValidationResult> => {
        const response = await apiClient.post<ValidationResult>('/scenarios/validate', {
            yaml_content: yamlContent,
        });
        return response.data;
    },

    create: async (filename: string, scenario: any): Promise<any> => {
        const response = await apiClient.post(`/scenarios/?filename=${filename}`, scenario);
        return response.data;
    },

    update: async (filename: string, scenario: any): Promise<any> => {
        const response = await apiClient.put(`/scenarios/${filename}`, scenario);
        return response.data;
    },

    delete: async (filename: string): Promise<any> => {
        const response = await apiClient.delete(`/scenarios/${filename}`);
        return response.data;
    }
};

export const MaterialsService = {
    list: async (): Promise<MaterialInfo[]> => {
        const response = await apiClient.get<MaterialInfo[]>('/materials/');
        return response.data;
    }
};
