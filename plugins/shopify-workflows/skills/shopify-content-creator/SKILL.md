---
name: shopify-content-creator
description: "Manage blog articles, pages, and theme assets for content creators. Use when creating blog posts, pages, or publishing content to Shopify stores."
license: MIT
---

# Shopify Content Creator Skill

**Purpose**: Manage blog articles, pages, and theme assets for content creators and writers using Shopify Admin API.

**When to use this skill**:
- Creating, updating, or deleting blog posts and articles
- Managing static pages (About, FAQ, Terms of Service, etc.)
- Publishing content workflows from markdown files
- Basic theme asset operations (CSS, JS, templates)
- Content scheduling and metadata management

**NOT for** (handled by other skills):
- Products, inventory, orders, customers → `shopify-merchant-daily`
- Discounts, campaigns, marketing → `shopify-marketing-ops`
- Webhooks, metafields, apps → `shopify-developer`
- Analytics queries → `shopify-analytics`

**Target Users**: Content managers, writers, bloggers, marketing teams

---

## Core Integration

### Shopify Dev MCP Setup

**ALWAYS start with learn_shopify_api**:
```javascript
// Step 1: Initialize conversation context
learn_shopify_api({
  api: "admin",
  conversationId: undefined // Will generate new ID
})
// Extract conversationId from response for all subsequent calls
```

**Schema Introspection Pattern**:
```javascript
// Step 2: Explore available operations
introspect_graphql_schema({
  conversationId: "YOUR_CONVERSATION_ID",
  api: "admin",
  query: "article", // Search for article-related operations
  filter: ["mutations", "types"]
})

// Common content operations:
// - "article" → articleCreate, articleUpdate, articleDelete
// - "blog" → blogCreate, blogUpdate
// - "page" → pageCreate, pageUpdate, pageDelete
// - "onlineStoreTheme" → theme asset operations
```

**Authentication**:
⚠️ **CRITICAL**: See [AUTHENTICATION.md](../../AUTHENTICATION.md) for complete authentication guide.

**Required Scopes**:
- `write_content` - Blog articles, pages
- `write_themes` - Theme assets (optional)

**Key Points**:
- Shopify Dev MCP validates GraphQL but does NOT execute mutations or handle authentication
- You MUST implement OAuth 2.0 client credentials grant flow yourself
- Tokens expire after 24 hours (86399 seconds) and must be refreshed
- Use access token in `X-Shopify-Access-Token` header for all API requests

**GraphQL Validation Pattern**:
```javascript
// Step 3: Always validate before execution
validate_graphql_codeblocks({
  conversationId: "YOUR_CONVERSATION_ID",
  api: "admin",
  codeblocks: [`
    mutation createArticle($input: ArticleCreateInput!) {
      articleCreate(article: $input) {
        article { id title }
        userErrors { field message }
      }
    }
  `]
})
```

---

## Blog Operations

### articleCreate Mutation

**Complete Example**:
```graphql
mutation createArticle($article: ArticleCreateInput!, $blogId: ID!) {
  articleCreate(article: $article, blogId: $blogId) {
    article {
      id
      title
      handle
      bodySummary
      publishedAt
      tags
      image {
        url
        altText
      }
      seo {
        title
        description
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

**Variables Structure**:
```json
{
  "blogId": "gid://shopify/Blog/123456789",
  "article": {
    "title": "Getting Started with Shopify",
    "bodyHtml": "<p>Your HTML content here...</p>",
    "author": "John Doe",
    "tags": ["tutorial", "getting-started"],
    "publishedAt": "2025-11-07T10:00:00Z",
    "image": {
      "url": "https://cdn.shopify.com/image.jpg",
      "altText": "Hero image"
    },
    "seo": {
      "title": "Getting Started with Shopify - Complete Guide",
      "description": "Learn how to set up your Shopify store in 10 easy steps."
    }
  }
}
```

**Key Fields**:
- `title` (required): Article title
- `bodyHtml` (required): HTML content body
- `author`: Author name (string)
- `tags`: Array of tag strings
- `publishedAt`: ISO 8601 timestamp (null = draft)
- `handle`: URL slug (auto-generated if omitted)
- `image`: Featured image with altText
- `seo`: Meta title and description overrides

### articleUpdate Mutation

**Example**:
```graphql
mutation updateArticle($id: ID!, $article: ArticleUpdateInput!) {
  articleUpdate(id: $id, article: $article) {
    article {
      id
      title
      handle
      publishedAt
    }
    userErrors {
      field
      message
    }
  }
}
```

**Variables**:
```json
{
  "id": "gid://shopify/OnlineStoreArticle/987654321",
  "article": {
    "title": "Updated Title",
    "bodyHtml": "<p>Updated content...</p>",
    "tags": ["updated", "revised"]
  }
}
```

### articleDelete Mutation

**Example**:
```graphql
mutation deleteArticle($id: ID!) {
  articleDelete(id: $id) {
    deletedId
    userErrors {
      field
      message
    }
  }
}
```

**Variables**:
```json
{
  "id": "gid://shopify/OnlineStoreArticle/987654321"
}
```

### Finding Blog IDs

**Query blogs first**:
```graphql
query getBlogs {
  blogs(first: 10) {
    edges {
      node {
        id
        handle
        title
      }
    }
  }
}
```

---

## Page Operations

### pageCreate Mutation

**Complete Example**:
```graphql
mutation createPage($page: PageCreateInput!) {
  pageCreate(page: $page) {
    page {
      id
      title
      handle
      bodySummary
      isPublished
      publishedAt
      seo {
        title
        description
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

**Variables Structure**:
```json
{
  "page": {
    "title": "About Us",
    "bodyHtml": "<h1>Our Story</h1><p>Founded in 2020...</p>",
    "handle": "about-us",
    "isPublished": true,
    "publishedAt": "2025-11-07T10:00:00Z",
    "seo": {
      "title": "About Us - Company Name",
      "description": "Learn about our mission and values."
    }
  }
}
```

**Key Fields**:
- `title` (required): Page title
- `bodyHtml` (required): HTML content
- `handle`: URL slug (e.g., "about-us" → /pages/about-us)
- `isPublished`: Boolean visibility flag
- `publishedAt`: Publication timestamp
- `templateSuffix`: Custom template (e.g., "contact")

### pageUpdate Mutation

**Example**:
```graphql
mutation updatePage($id: ID!, $page: PageUpdateInput!) {
  pageUpdate(id: $id, page: $page) {
    page {
      id
      title
      handle
      isPublished
    }
    userErrors {
      field
      message
    }
  }
}
```

### pageDelete Mutation

**Example**:
```graphql
mutation deletePage($id: ID!) {
  pageDelete(id: $id) {
    deletedId
    userErrors {
      field
      message
    }
  }
}
```

---

## Theme Assets

### Basic File Operations

**Query current theme**:
```graphql
query getOnlineStoreTheme {
  themes(first: 1, roles: MAIN) {
    edges {
      node {
        id
        name
        role
      }
    }
  }
}
```

**Asset structure** (via REST API for file operations):
- Theme assets typically managed through REST API
- GraphQL focuses on content, not theme files
- Use Admin REST API for uploading CSS/JS/Liquid templates

**Common theme asset paths**:
- `assets/custom.css` - Custom stylesheets
- `assets/custom.js` - Custom JavaScript
- `snippets/custom-snippet.liquid` - Reusable Liquid snippets
- `sections/custom-section.liquid` - Page sections

**Note**: For production theme management, use Shopify CLI:
```bash
shopify theme push
shopify theme pull
shopify theme dev
```

---

## Error Handling

### userErrors Pattern

**All content mutations return userErrors array**:
```graphql
{
  articleCreate(article: $input, blogId: $blogId) {
    article { id }
    userErrors {
      field      # Which input field caused error
      message    # Human-readable error message
    }
  }
}
```

**Common userErrors**:
- `field: ["title"], message: "Title can't be blank"`
- `field: ["bodyHtml"], message: "Body can't be blank"`
- `field: ["handle"], message: "Handle has already been taken"`
- `field: ["publishedAt"], message: "Published at is invalid"`

**Error Handling Pattern**:
```javascript
const response = await articleCreate(variables);

if (response.userErrors && response.userErrors.length > 0) {
  console.error("Article creation failed:");
  response.userErrors.forEach(err => {
    console.error(`- ${err.field.join('.')}: ${err.message}`);
  });
  return null;
}

return response.article;
```

**Validation Before Mutation**:
1. Check required fields (title, bodyHtml)
2. Validate handle format (lowercase, hyphens, no spaces)
3. Verify ISO 8601 timestamp format for publishedAt
4. Ensure blog/page IDs exist before referencing
5. Validate HTML structure in bodyHtml

---

## Complete Workflow Examples

### Example 1: Create Blog Post from Markdown File

**Workflow Steps**:
```javascript
// Step 1: Read markdown file
const markdownContent = readFile("blog-post.md");

// Step 2: Parse frontmatter
const { frontmatter, content } = parseMarkdown(markdownContent);
// frontmatter = { title, author, tags, publishedAt, seo }
// content = markdown body

// Step 3: Convert markdown to HTML
const bodyHtml = markdownToHtml(content);

// Step 4: Get blog ID
const blogsQuery = `
  query getBlogs {
    blogs(first: 10) {
      edges {
        node {
          id
          handle
        }
      }
    }
  }
`;
const blogId = "gid://shopify/Blog/123456789"; // From query response

// Step 5: Validate GraphQL mutation
validate_graphql_codeblocks({
  conversationId: "conv-123",
  api: "admin",
  codeblocks: [`
    mutation createArticle($article: ArticleCreateInput!, $blogId: ID!) {
      articleCreate(article: $article, blogId: $blogId) {
        article { id title handle publishedAt }
        userErrors { field message }
      }
    }
  `]
});

// Step 6: Execute mutation
const variables = {
  blogId: blogId,
  article: {
    title: frontmatter.title,
    bodyHtml: bodyHtml,
    author: frontmatter.author,
    tags: frontmatter.tags,
    publishedAt: frontmatter.publishedAt,
    seo: {
      title: frontmatter.seo?.title || frontmatter.title,
      description: frontmatter.seo?.description
    }
  }
};

// Step 7: Handle response
if (response.userErrors.length === 0) {
  console.log(`✅ Article created: ${response.article.handle}`);
} else {
  console.error("❌ Failed to create article");
}
```

**Example markdown file**:
```markdown
---
title: "Getting Started with Shopify"
author: "John Doe"
tags: ["tutorial", "getting-started"]
publishedAt: "2025-11-07T10:00:00Z"
seo:
  title: "Getting Started with Shopify - Complete Guide"
  description: "Learn how to set up your Shopify store in 10 easy steps."
---

# Welcome to Shopify

Your content here...
```

### Example 2: Bulk Update Article Tags

**Workflow**:
```javascript
// Step 1: Query existing articles
const articlesQuery = `
  query getArticles($blogId: ID!) {
    blog(id: $blogId) {
      articles(first: 50) {
        edges {
          node {
            id
            title
            tags
          }
        }
      }
    }
  }
`;

// Step 2: Filter articles needing updates
const articlesToUpdate = articles.filter(article =>
  article.tags.includes("old-tag")
);

// Step 3: Update each article
for (const article of articlesToUpdate) {
  const newTags = article.tags
    .filter(tag => tag !== "old-tag")
    .concat(["new-tag"]);

  const variables = {
    id: article.id,
    article: {
      tags: newTags
    }
  };

  // Execute articleUpdate mutation
  await updateArticle(variables);
}
```

### Example 3: Create Static Pages Set

**Workflow for common pages**:
```javascript
const staticPages = [
  {
    title: "About Us",
    handle: "about",
    bodyHtml: "<h1>Our Story</h1><p>...</p>",
    templateSuffix: "page.about"
  },
  {
    title: "Contact",
    handle: "contact",
    bodyHtml: "<h1>Get in Touch</h1><form>...</form>",
    templateSuffix: "page.contact"
  },
  {
    title: "FAQ",
    handle: "faq",
    bodyHtml: "<h1>Frequently Asked Questions</h1><dl>...</dl>"
  }
];

// Validate mutation once
validate_graphql_codeblocks({
  conversationId: "conv-123",
  api: "admin",
  codeblocks: [`
    mutation createPage($page: PageCreateInput!) {
      pageCreate(page: $page) {
        page { id title handle }
        userErrors { field message }
      }
    }
  `]
});

// Create all pages
for (const pageData of staticPages) {
  const variables = { page: { ...pageData, isPublished: true } };
  const response = await createPage(variables);

  if (response.userErrors.length === 0) {
    console.log(`✅ Created page: /pages/${response.page.handle}`);
  }
}
```

---

## Best Practices

**Content Publishing**:
1. Draft first: Create with `publishedAt: null`, review, then update with timestamp
2. SEO optimization: Always provide custom seo.title and seo.description
3. Image optimization: Use Shopify CDN URLs, provide meaningful altText
4. Handle generation: Let Shopify auto-generate handles to avoid conflicts

**Performance**:
- Batch queries using GraphQL connections (first: 50)
- Use fragments for repeated field selections
- Request only needed fields to minimize response size

**Validation**:
- Always validate GraphQL with validate_graphql_codeblocks before execution
- Check userErrors array after every mutation
- Verify blog/page IDs exist before creating articles/pages

**Markdown Conversion**:
- Use reliable markdown parser (e.g., marked, markdown-it)
- Sanitize HTML output to prevent XSS
- Preserve frontmatter metadata for Shopify fields mapping
- Handle code blocks, images, and links appropriately
