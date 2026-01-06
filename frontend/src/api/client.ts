/*
 * Copyright (C) 2026 Thomas
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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

export const SimulationService = {
    runAsync: async (payload: any): Promise<{ job_id: string, ws_url: string }> => {
        const response = await apiClient.post<{ job_id: string, ws_url: string }>('/simulation/run-async', payload);
        return response.data;
    }
};
