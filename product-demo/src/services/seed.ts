import type { Editors, Source } from '../domain/types.ts'

const column = (name: string, label: string, data_type = 'string', primary_key = false, position = 0) =>
  ({ name, label, data_type, nullable: !primary_key, primary_key, position })

export const sources: Source[] = [
  { id: '1', name: '营销业务应用', type: 'MySQL', host: '营销库（示例）', database: 'yx186', tables: [
    { name: 'C_CONS', label: '用电客户', columns: [
      column('CONS_NO', '户号', 'string', true, 0), column('CONS_NAME', '客户名称', 'string', false, 1),
      column('ELEC_ADDR', '用电地址', 'string', false, 2), column('CONTRACT_CAP', '合同容量', 'decimal', false, 3),
    ] },
    { name: 'A_RCVBL_FLOW', label: '应收电费', columns: [
      column('RCVBL_ID', '应收标识', 'integer', true, 0), column('CONS_NO', '户号', 'string', false, 1),
      column('RCVBL_AMT', '应收金额', 'decimal', false, 2), column('RCVED_AMT', '实收金额', 'decimal', false, 3),
      column('SETTLE_FLAG', '结清标志', 'string', false, 4),
    ] },
  ] },
]

export const reference = (schema: string, table: string, sourceId = '1') => ({
  teiid_id: 'local-demo', data_source_id: sourceId, schema_name: schema, table_name: table,
  active_vdb_version: '1', data_source_revision: '1', model_name: schema,
  query_availability: 'available', columns_truncated: false,
})

export const editors: Editors = {
  model: {
    format_version: 'wing-model-editor/1',
    concepts: [
      { id: 'Consumer', name: '用电客户', english_name: 'Consumer', top_category: 'participant', parents: [], disjoint_with: [], description: '营销业务中的用电客户。' },
      { id: 'Receivable', name: '应收电费', english_name: 'Receivable', top_category: 'account', parents: [], disjoint_with: [], description: '客户应收与实收电费记录。' },
      { id: 'ArrearsConsumer', name: '欠费客户', english_name: 'ArrearsConsumer', top_category: 'participant', parents: ['Consumer'], disjoint_with: [], description: '存在未结清应收记录的客户。' },
    ],
    attributes: [
      { id: 'Consumer_consNo', name: '户号', concept_id: 'Consumer', datatype: 'string', aliases: ['用户编号', '客户编号'], sensitivity: 'internal' },
      { id: 'Consumer_name', name: '客户名称', concept_id: 'Consumer', datatype: 'string', aliases: ['户名', '用户名称'], sensitivity: 'internal' },
      { id: 'Consumer_address', name: '用电地址', concept_id: 'Consumer', datatype: 'string', aliases: ['地址'], sensitivity: 'internal' },
      { id: 'Consumer_capacity', name: '合同容量', concept_id: 'Consumer', datatype: 'decimal', aliases: ['容量'], sensitivity: 'internal' },
      { id: 'Receivable_id', name: '应收标识', concept_id: 'Receivable', datatype: 'integer', aliases: [], sensitivity: 'internal' },
      { id: 'Receivable_amount', name: '应收金额', concept_id: 'Receivable', datatype: 'decimal', aliases: ['应收电费'], sensitivity: 'internal' },
      { id: 'Receivable_received', name: '实收金额', concept_id: 'Receivable', datatype: 'decimal', aliases: ['实收电费'], sensitivity: 'internal' },
      { id: 'Receivable_settled', name: '结清标志', concept_id: 'Receivable', datatype: 'string', aliases: [], sensitivity: 'internal' },
    ],
    relations: [
      { id: 'Receivable_consumer', name: '应收客户', source_id: 'Receivable', target_id: 'Consumer', symmetric: false, transitive: false, functional: true },
    ],
    annotations: [
      { subject: 'Receivable_amount', key: 'demo:calculation', value: JSON.stringify({
        label: '欠费金额', formula: 'RCVBL_AMT - RCVED_AMT', filters: ["SETTLE_FLAG = '0'"],
        inputs: ['Receivable_amount', 'Receivable_received'],
      }) },
    ],
  },
  pipeline: {
    format_version: 'wing-pipeline-editor/2',
    fact_planes: [reference('yx186', 'C_CONS'), reference('yx186', 'A_RCVBL_FLOW')],
    bindings: [
      { ...reference('yx186', 'C_CONS'), id: 'consumer', concept_id: 'Consumer', identity_scope: 'Consumer', key_columns: ['CONS_NO'], attributes: [
        { attribute_id: 'Consumer_consNo', column: 'CONS_NO' }, { attribute_id: 'Consumer_name', column: 'CONS_NAME' },
        { attribute_id: 'Consumer_address', column: 'ELEC_ADDR' }, { attribute_id: 'Consumer_capacity', column: 'CONTRACT_CAP' },
      ], references: [] },
      { ...reference('yx186', 'A_RCVBL_FLOW'), id: 'receivable', concept_id: 'Receivable', identity_scope: 'Receivable', key_columns: ['RCVBL_ID'], attributes: [
        { attribute_id: 'Receivable_id', column: 'RCVBL_ID' }, { attribute_id: 'Receivable_amount', column: 'RCVBL_AMT' },
        { attribute_id: 'Receivable_received', column: 'RCVED_AMT' }, { attribute_id: 'Receivable_settled', column: 'SETTLE_FLAG' },
      ], references: [{ relation_id: 'Receivable_consumer', parent_binding_id: 'consumer', joins: [{ child: 'CONS_NO', parent: 'CONS_NO' }] }] },
    ],
  },
  rules: {
    format_version: 'wing-rules-editor/2',
    rules: [{
      id: 'arrearsConsumer', name: '欠费客户认定', level: 'FR', calibration: 'pending', enabled: true,
      nl: '应收电费未结清，则该记录对应的客户是欠费客户。',
      source: '示例规则，口径以实际业务确认为准。',
      body: { op: 'all', items: [
        { kind: 'class', predicate: 'Receivable', args: [{ var: 'r' }] },
        { kind: 'attribute', predicate: 'Receivable_settled', args: [{ var: 'r' }, { literal: { value: '0', datatype: 'string' } }] },
        { kind: 'relation', predicate: 'Receivable_consumer', args: [{ var: 'r' }, { var: 'c' }] },
      ] },
      head: { kind: 'class', predicate: 'ArrearsConsumer', args: [{ var: 'c' }] },
    }],
    constraints: [],
  },
}
