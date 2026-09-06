import React, { useState } from "react";
import { Card, Typography, Input, Button, Upload, Table, Tag, Space, Modal, Tabs, Popconfirm, Spin, Empty, Descriptions } from "antd";
import { SearchOutlined, UploadOutlined, DeleteOutlined, DatabaseOutlined, LinkOutlined } from "@ant-design/icons";
import { useKnowledgeSearch, useKnowledgeDocs, useKnowledgeDoc, useKnowledgeStats, useUploadDocument, useIndexWebContent, useDeleteDocument } from "../../hooks/useKnowledge";
import { DOC_TYPE_LABELS, type KnowledgeDocument } from "../../api/knowledge";

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

const TYPE_COLORS: Record<string, string> = { pdf: "red", markdown: "blue", txt: "default", code: "green", web: "orange" };

const KnowledgeBase: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeQuery, setActiveQuery] = useState("");
  const [viewDocId, setViewDocId] = useState<string | null>(null);
  const [webModalOpen, setWebModalOpen] = useState(false);
  const [webContent, setWebContent] = useState("");
  const [webFilename, setWebFilename] = useState("");
  const { data: searchResults, isLoading: searchLoading } = useKnowledgeSearch(activeQuery);
  const { data: docsData } = useKnowledgeDocs();
  const { data: statsData } = useKnowledgeStats();
  const { data: viewDoc } = useKnowledgeDoc(viewDocId || "");
  const uploadMut = useUploadDocument();
  const webMut = useIndexWebContent();
  const deleteMut = useDeleteDocument();

  const handleSearch = () => setActiveQuery(searchQuery);
  const handleUpload = (file: File) => { uploadMut.mutate(file); return false; };
  const handleWebSubmit = () => { webMut.mutate({ content: webContent, filename: webFilename }); setWebModalOpen(false); setWebContent(""); setWebFilename(""); };

  const columns = [
    { title: "标题", dataIndex: "title", key: "title", ellipsis: true },
    { title: "类型", dataIndex: "doc_type", width: 100, render: (t: string) => <Tag color={TYPE_COLORS[t]}>{DOC_TYPE_LABELS[t] || t}</Tag> },
    { title: "分块数", dataIndex: "chunk_count", width: 80 },
    { title: "标签", dataIndex: "tags", width: 200, render: (tags: string[]) => tags?.map((t: string) => <Tag key={t}>{t}</Tag>) || null },
    { title: "操作", key: "actions", width: 120, render: (_: unknown, r: KnowledgeDocument) => (
      <Space><Button size="small" onClick={() => setViewDocId(r.id)}>查看</Button>
      <Popconfirm title="确定删除？" onConfirm={() => deleteMut.mutate(r.id)}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm></Space>) },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <Title level={2}><DatabaseOutlined /> Knowledge Base</Title>
      <Paragraph type="secondary">Upload documents, index web content, and search your personal knowledge.</Paragraph>
      <Tabs defaultActiveKey="docs" items={[
        { key: "docs", label: "文档", children: (docsData?.documents || []).length === 0 ? <Empty description="暂无文档" /> : (
          <Table rowKey="id" dataSource={docsData?.documents || []} columns={columns} size="middle" onRow={(r) => ({ onClick: () => setViewDocId(r.id), style: { cursor: "pointer" } })} pagination={{ pageSize: 15 }} />) },
        { key: "search", label: "搜索", children: (<>
          <Space style={{ marginBottom: 16 }} wrap>
            <Input.Search placeholder="搜索知识..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} onSearch={handleSearch} style={{ width: 320 }} />
            <Upload beforeUpload={handleUpload} showUploadList={false}><Button icon={<UploadOutlined />}>上传文件</Button></Upload>
            <Button icon={<LinkOutlined />} onClick={() => setWebModalOpen(true)}>网页内容</Button>
          </Space>
          {searchLoading ? <Spin /> : (searchResults?.results || []).length === 0 ? <Empty /> : (
            <Table rowKey="chunk_id" dataSource={searchResults?.results || []} columns={[
              { title: "标题", dataIndex: "title", ellipsis: true },
              { title: "内容", dataIndex: "content", ellipsis: true, render: (t: string) => t?.slice(0, 200) },
              { title: "相关度", dataIndex: "score", width: 80, render: (v: number) => v?.toFixed(2) },
            ]} size="middle" pagination={{ pageSize: 15 }} />)}
        </>) },
      ]} />
      <Modal title="文档详情" open={!!viewDocId} onCancel={() => setViewDocId(null)} footer={null} width={700}>
        {viewDoc?.document && (<Descriptions column={1} bordered size="small">
          <Descriptions.Item label="标题">{viewDoc.document.title}</Descriptions.Item>
          <Descriptions.Item label="类型"><Tag color={TYPE_COLORS[viewDoc.document.doc_type]}>{DOC_TYPE_LABELS[viewDoc.document.doc_type]}</Tag></Descriptions.Item>
          <Descriptions.Item label="标签">{viewDoc.document.tags?.map((t: string) => <Tag key={t}>{t}</Tag>)}</Descriptions.Item>
          <Descriptions.Item label="摘要">{viewDoc.document.summary}</Descriptions.Item>
          <Descriptions.Item label="分块数">{(viewDoc.chunks || []).length}</Descriptions.Item>
        </Descriptions>)}
      </Modal>
      <Modal title="添加网页内容" open={webModalOpen} onOk={handleWebSubmit} onCancel={() => setWebModalOpen(false)}>
        <TextArea rows={6} placeholder="在此粘贴内容..." value={webContent} onChange={(e) => setWebContent(e.target.value)} style={{ marginBottom: 12 }} />
        <Input placeholder="可选文件名" value={webFilename} onChange={(e) => setWebFilename(e.target.value)} />
      </Modal>
    </div>
  );
};

export default KnowledgeBase;
