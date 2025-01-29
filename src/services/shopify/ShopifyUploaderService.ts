import { GraphQLClient } from 'graphql-request';

export interface ShopifyArticleInput {
  title: string;
  content: string;
  excerpt: string;
  image?: {
    url: string;
    altText?: string;
  };
}

export interface ShopifyArticleResponse {
  id: string;
  title: string;
  handle: string;
  body: string;
  summary: string;
  tags: string[];
  image?: {
    altText: string;
    originalSrc: string;
  };
}

export class ShopifyUploaderService {
  private client: GraphQLClient;
  private blogId: string = 'gid://shopify/Blog/85728755847';
  private author: string = 'Jackson Blacklock';

  constructor(shopifyStoreUrl: string, accessToken: string, apiVersion: string) {
    const endpoint = `https://${shopifyStoreUrl}/admin/api/${apiVersion}/graphql.json`;
    this.client = new GraphQLClient(endpoint, {
      headers: {
        'X-Shopify-Access-Token': accessToken,
        'Content-Type': 'application/json',
      },
    });
  }

  async uploadPost(post: ShopifyArticleInput): Promise<ShopifyArticleResponse> {
    try {
      // Validate input
      this.validatePostInput(post);

      // Prepare article data
      const articleData = {
        blogId: this.blogId,
        title: post.title,
        author: {
          name: this.author
        },
        body: post.content,
        summary: post.excerpt,
        isPublished: false
      };

      // Add image if provided
      if (post.image?.url) {
        Object.assign(articleData, {
          image: {
            altText: post.image.altText || post.title,
            src: post.image.url
          }
        });
      }

      const mutation = `
        mutation CreateArticle($article: ArticleCreateInput!) {
          articleCreate(article: $article) {
            article {
              id
              title
              handle
              body
              summary
              tags
              image {
                altText
                originalSrc
              }
            }
            userErrors {
              code
              field
              message
            }
          }
        }
      `;

      const variables = {
        article: articleData
      };

      const response = await this.client.request<{
        articleCreate: {
          article: ShopifyArticleResponse;
          userErrors: Array<{
            code: string;
            field: string;
            message: string;
          }>;
        };
      }>(mutation, variables);

      // Check for user errors
      const { article, userErrors } = response.articleCreate;
      if (userErrors && userErrors.length > 0) {
        const errorMessages = userErrors
          .map(error => `${error.field}: ${error.message}`)
          .join(', ');
        throw new Error(`Shopify API Errors: ${errorMessages}`);
      }

      console.log(`Post uploaded successfully: ${article.title} - ${article.summary}`);
      return article;

    } catch (error) {
      console.error(`Error uploading post: ${post.title}`);
      console.error(error);
      throw new Error(`Shopify upload error: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private validatePostInput(post: ShopifyArticleInput): void {
    if (!post.title?.trim()) {
      throw new Error('Title cannot be empty');
    }
    if (!post.content?.trim()) {
      throw new Error('Content cannot be empty');
    }
    if (!post.excerpt?.trim()) {
      throw new Error('Excerpt cannot be empty');
    }
    if (post.image?.url && !post.image.url.startsWith('http')) {
      throw new Error('Invalid image URL format');
    }
  }
}