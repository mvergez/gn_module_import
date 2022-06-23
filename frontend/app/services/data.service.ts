import { Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { HttpClient, HttpHeaders, HttpParams } from "@angular/common/http";
import { AppConfig } from "@geonature_config/app.config";
import { ModuleConfig } from "../module.config";
import { Dataset, Import, ImportError, ImportValues, SynthesisThemeFields, TaxaDistribution } from "../models/import.model";
import { FieldMapping, FieldMappingValues, ContentMapping, ContentMappingValues } from "../models/mapping.model";

const urlApi = `${AppConfig.API_ENDPOINT}/${ModuleConfig.MODULE_URL}`;

@Injectable()
export class DataService {
  constructor(private _http: HttpClient) { }

  getNomenclatures(): Observable<ImportValues> {
    return this._http.get<ImportValues>(`${urlApi}/nomenclatures`);
  }

  getImportList(values): Observable<Array<Import>> {
    const url = `${urlApi}/imports/`
    let params = new HttpParams({fromObject:values})
    return this._http.get<Array<Import>>(url, { params: params });
  }

  getOneImport(id_import): Observable<Import> {
    return this._http.get<Import>(`${urlApi}/imports/${id_import}/`);
  }


  addFile(datasetId: number, file: File): Observable<Import> {
    let fd = new FormData();
    fd.append("file", file, file.name);
    fd.append("datasetId", String(datasetId));
    const url = `${urlApi}/imports/upload`;
    return this._http.post<Import>(url, fd);
  }

  updateFile(importId: number, file: File): Observable<Import> {
    let fd = new FormData();
    fd.append("file", file, file.name);
    const url = `${urlApi}/imports/${importId}/upload`;
    return this._http.put<Import>(url, fd);
  }

  decodeFile(importId: number, params: { encoding: string, format: string, srid: string}, decode:number=1): Observable<Import> {
    const url = `${urlApi}/imports/${importId}/decode?decode=${decode}`;
    return this._http.post<Import>(url, params);
  }

  loadImport(importId: number): Observable<Import> {
    const url = `${urlApi}/imports/${importId}/load`;
    return this._http.post<Import>(url, null);
  }

  updateImport(idImport, data): Observable<Import> {
    return this._http.post<Import>(`${urlApi}/imports/${idImport}/update`, data);
  }

  createFieldMapping(name: string, values: FieldMappingValues): Observable<FieldMapping> {
    return this._http.post<FieldMapping>(`${urlApi}/fieldmappings/?label=${name}`, values);
  }

  createContentMapping(name: string, values: ContentMappingValues): Observable<ContentMapping> {
    return this._http.post<ContentMapping>(`${urlApi}/contentmappings/?label=${name}`, values);
  }

  getFieldMappings(): Observable<Array<FieldMapping>> {
    return this._http.get<Array<FieldMapping>>(`${urlApi}/fieldmappings/`);
  }

  getContentMappings(): Observable<Array<ContentMapping>> {
    return this._http.get<Array<ContentMapping>>(`${urlApi}/contentmappings/`);
  }

  getFieldMapping(id_mapping: number): Observable<FieldMapping> {
    return this._http.get<FieldMapping>(`${urlApi}/fieldmappings/${id_mapping}/`);
  }

  getContentMapping(id_mapping: number): Observable<ContentMapping> {
    return this._http.get<ContentMapping>(`${urlApi}/contentmappings/${id_mapping}/`);
  }

  updateFieldMapping(id_mapping: number, values: FieldMappingValues, label: string = ''): Observable<FieldMapping> {
    let url =  `${urlApi}/fieldmappings/${id_mapping}/`
    if (label) {
        url  = url + `?label=${label}`
    }
    return this._http.post<FieldMapping>(url, values);
  }

  updateContentMapping(id_mapping: number, values: ContentMappingValues, label: string = ''): Observable<ContentMapping> {
    let url =  `${urlApi}/contentmappings/${id_mapping}/`
    if (label) {
        url  = url + `?label=${label}`
    }
    return this._http.post<ContentMapping>(url, values);
  }

  renameFieldMapping(id_mapping: number, label: string): Observable<FieldMapping> {
    return this._http.post<FieldMapping>(`${urlApi}/fieldmappings/${id_mapping}/?label=${label}`, null);
  }

  renameContentMapping(id_mapping: number, label: string): Observable<ContentMapping> {
    return this._http.post<ContentMapping>(`${urlApi}/contentmappings/${id_mapping}/?label=${label}`, null);
  }

  deleteFieldMapping(id_mapping: number): Observable<null> {
    return this._http.delete<null>(`${urlApi}/fieldmappings/${id_mapping}/`);
  }

  deleteContentMapping(id_mapping: number): Observable<null> {
    return this._http.delete<null>(`${urlApi}/contentmappings/${id_mapping}/`);
  }

  /**
   * Perform all data checking on the table (content et field)
   * @param idImport
   * @param idFieldMapping
   * @param idContentMapping
   */
  /*dataChecker(idImport, idFieldMapping, idContentMapping): Observable<Import> {
    const url = `${urlApi}/data_checker/${idImport}/field_mapping/${idFieldMapping}/content_mapping/${idContentMapping}`;
    return this._http.post<Import>(url, new FormData());
  }*/

  deleteImport(importId: number): Observable<void> {
    return this._http.delete<void>(`${urlApi}/imports/${importId}/`);
  }

  /**
   * Return all the column of the file of an import
   * @param idImport : integer
   */
  getColumnsImport(idImport: number): Observable<Array<string>> {
    return this._http.get<Array<string>>(`${urlApi}/imports/${idImport}/columns`);
  }

  getImportValues(idImport: number): Observable<ImportValues> {
    return this._http.get<ImportValues>(`${urlApi}/imports/${idImport}/values`);
  }

  getBibFields(): Observable<Array<SynthesisThemeFields>> {
    return this._http.get<Array<SynthesisThemeFields>>(`${urlApi}/synthesis/fields`);
  }

  setImportFieldMapping(idImport: number, values: FieldMappingValues): Observable<Import> {
    return this._http.post<Import>(`${urlApi}/imports/${idImport}/fieldmapping`, values);
  }

  setImportContentMapping(idImport: number, values: ContentMappingValues): Observable<Import> {
    return this._http.post<Import>(`${urlApi}/imports/${idImport}/contentmapping`, values);
  }

  getNomencInfo(id_import: number) {
    return this._http.get<any>(
      `${urlApi}/imports/${id_import}/contentMapping`
    );
  }

  prepareImport(import_id: number): Observable<Import> {
    return this._http.post<Import>(`${urlApi}/imports/${import_id}/prepare`, {});
  }

  getValidData(import_id: number): Observable<any> {
    return this._http.get<any>(`${urlApi}/imports/${import_id}/preview_valid_data`);
  }

  finalizeImport(import_id): Observable<Import> {
    return this._http.post<Import>(`${urlApi}/imports/${import_id}/import`, {});
  }

  getErrorCSV(importId: number) {
    return this._http.get(`${urlApi}/imports/${importId}/invalid_rows`, {
      responseType: "blob"
    });
  }

  getImportErrors(importId): Observable<Array<ImportError>> {
    return this._http.get<Array<ImportError>>(`${urlApi}/imports/${importId}/errors`);
  }

  getTaxaRepartition(sourceId: number, taxa_rank: string) {
    return this._http.get<Array<TaxaDistribution>>(
      `${AppConfig.API_ENDPOINT}/synthese/taxa_distribution`,
      {
        params: {
          id_source: sourceId,
          taxa_rank: taxa_rank,
        },
      }
    );
  }

  getDatasetFromId(datasetId: number) {
    return this._http.get<Dataset>(
      `${AppConfig.API_ENDPOINT}/meta/dataset/${datasetId}`
    );
  }

  getPdf(importId, mapImg, chartImg) {
    const formData = new FormData();
    formData.append("map", mapImg);
    formData.append("chart", chartImg);
    return this._http
      .post(`${urlApi}/export_pdf/${importId}`, formData, { responseType: "blob",
      });
    // return this._http.get(`${urlApi}/export_pdf/${importId}`, {responseType: 'blob'})
  }
}
