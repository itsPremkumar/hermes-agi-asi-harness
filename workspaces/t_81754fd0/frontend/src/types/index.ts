export interface GenerationResult {
  id: string;
  framework: string;
  html_code: string;
  css_code: string;
  jsx_code: string;
  vue_code: string;
  angular_code: string;
  components_used: string[];
  responsive: boolean;
  accessible: boolean;
}

export interface Component {
  id: string;
  name: string;
  category: string;
  description: string;
  html_template: string;
  react_template: string;
  vue_template: string;
  angular_template: string;
  tags: string[];
  responsive: boolean;
  accessible: boolean;
}
