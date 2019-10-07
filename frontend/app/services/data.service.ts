import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { AppConfig } from '@geonature_config/app.config';
import { ModuleConfig } from '../module.config';


const HttpUploadOptions = {
	headers: new HttpHeaders({ Accept: 'application/json' })
};
const urlApi = `${AppConfig.API_ENDPOINT}/${ModuleConfig.MODULE_URL}`;

@Injectable()
export class DataService {
	constructor(private _http: HttpClient) {}


	getImportList() {
		return this._http.get<any>(urlApi);
	}


	postUserFile(value, datasetId, importId) {
		const urlStatus = `${urlApi}/uploads`;
		let fd = new FormData();
		fd.append('File', value.file, value.file['name']);
		fd.append('encodage', value.encodage);
		fd.append('srid', value.srid);
		fd.append('separator', value.separator);
		fd.append('datasetId', datasetId);
		fd.append('importId', importId);
		return this._http.post<any>(urlStatus, fd, HttpUploadOptions);
	}


	getUserDatasets() {
		return this._http.get<any>(`${urlApi}/datasets`);
    }
    

	getFieldMappings() {
		return this._http.get<any>(`${urlApi}/field_mappings`);
    }
    

    getMappingFields(id_mapping: number) {
		return this._http.get<any>(`${urlApi}/field_mappings/${id_mapping}`);
    }
    

    postMappingFieldName(value) {
        const urlMapping = `${urlApi}/mappingFieldName`;
        return this._http.post<any>(urlMapping, value);
    }


	cancelImport(importId: number) {
		return this._http.get<any>(`${urlApi}/cancel_import/${importId}`);
	}


	getSynColumnNames() {
		return this._http.get<any>(`${urlApi}/syntheseInfo`);
	}


	postMapping(value, importId: number, id_mapping: number, user_srid) {
        const urlMapping = `${urlApi}/mapping/${importId}/${id_mapping}`;
        let fd = new FormData();
        for (let key of Object.keys(value)) {
            fd.append(key, value[key]);
        }
        fd.append('srid', user_srid);
		return this._http.post<any>(urlMapping, fd, HttpUploadOptions);
	}


	delete_aborted_step1() {
		return this._http.get<any>(`${urlApi}/delete_step1`);
    }
    
    
    postMetaToStep3(import_id, id_mapping, selected_columns, table_name) {
        let fd = new FormData();
        fd.append('import_id', import_id);
        fd.append('id_mapping', id_mapping);
        for (let key of Object.keys(selected_columns)) {
            fd.append(key, selected_columns[key]);
        }
        fd.append('table_name', table_name);
        return this._http.post<any>(`${urlApi}/postMetaToStep3`, fd, HttpUploadOptions);
    }

}