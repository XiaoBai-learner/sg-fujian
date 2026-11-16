export type Page = 'sources' | 'modeling' | 'agent'
export type Row = Record<string, unknown>
export interface Attribute { id: string; name: string; concept_id: string; datatype: string; aliases: string[]; [key: string]: unknown }
export interface Model { format_version: string; concepts: Row[]; attributes: Attribute[]; relations: Row[]; annotations: Row[] }
export interface Binding { id: string; concept_id: string; schema_name: string; table_name: string; key_columns: string[]; attributes: { attribute_id: string; column: string }[]; references: Row[]; [key: string]: unknown }
export interface Editors { model: Model; pipeline: { format_version: string; fact_planes: Row[]; bindings: Binding[] }; rules: { format_version: string; rules: Row[]; constraints: Row[] } }
export interface Column { name: string; label: string; data_type: string; nullable: boolean; primary_key: boolean; position: number }
export interface Source { id: string; name: string; type: string; host: string; database: string; tables: { name: string; label: string; columns: Column[] }[] }
export interface Material { id: string; name: string; kind: string; size: number }
export interface Result { label: string; status: 'located' | 'ambiguous' | 'not_found'; kind: 'direct' | 'calculated' | 'rule'; sources: { column: string; label: string; concept: string }[]; evidence: string[]; calculation?: { formula: string; filters: string[] }; rule?: string }
export interface Turn { id: string; question: string; ocr: string; revision: number; results: Result[] }
export interface Workspace { sources: Source[]; materials: Material[]; editors: Editors; revision: number; active: { revision: number; editors: Editors }; turns: Turn[] }
