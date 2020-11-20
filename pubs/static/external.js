const insertScript = (path) =>
  new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = path;
    s.onload = () => resolve(s);  // resolve with script, not event
    s.onerror = reject;
    document.body.appendChild(s);
  });

var loadDeps = async function(baseurl){
    let scripts = [
      insertScript('https://cdn.jsdelivr.net/npm/vue@2.6.12'),
      insertScript('https://cdn.jsdelivr.net/npm/vue-async-computed@3.9.0'),
      insertScript('https://cdn.jsdelivr.net/npm/axios@0.21.0'),
      insertScript('https://cdn.jsdelivr.net/npm/lodash@4.17.20')
    ]
    const s = document.createElement('link');
    s.rel = 'stylesheet';
    s.href = baseurl+'/static/main.css';
    document.head.appendChild(s);
    await Promise.all(scripts);
};

const pub_html = `
<div class="publication_filters"><form action="javascript:void(0);" autocomplete="off">
  <div class="input vcenter search"><label for="search">Text search: </label><input type="text" name="search" v-model.trim="filters.search" /></div>
  <div class="col">
    <div class="input vcenter"><label for="start_date">Start date: </label><input type="date" name="start_date" v-model="filters.start_date" /></div>
    <div class="input vcenter"><label for="end_date">End date: </label><input type="date" name="end_date" v-model="filters.end_date" /></div>
    <div class="input"><label for="type">Type: </label><div class="type_box">
      <div class="checkbox" v-for="t in  Object.keys(publication_types)">
        <input type="checkbox" name="type" :id="'type_'+t" :value="t" v-model="filters.type" :disabled="type_disabled(t)" />
        <label :for="'type_'+t">{{ publication_types[t] }}</label>
      </div>
    </div></div>
  </div><div class="col" v-if="!filters.hide_projects">
    <div class="input"><label for="projects">Project: </label><div class="projects_box">
      <div class="checkbox" v-for="p in  Object.keys(projects)">
        <input type="checkbox" name="projects" :id="'projects_'+p" :value="p" v-model="filters.projects" />
        <label :for="'projects_'+p">{{ projects[p] }}</label>
      </div>
    </div></div>
  </div>
</form></div>
<div class="publication_list">
  <h2>Publications</h2>
  <div v-if="typing">{{ typing }}</div>
  <div v-else>
    <pub v-for="pub in pubs" v-bind="pub" :project_labels="projects"></pub>
  </div>
</div>
`;

async function Pubs(id, baseurl = 'https://publications.icecube.aq', filters = {}) {
  await loadDeps(baseurl);

  var updatePubs = async function(filters) {
    console.log('getting pubs for filters:')
    console.log(filters)
    const response = await axios.get(baseurl+'/api/publications', {
      params: filters,
      paramsSerializer: function(p){
        let ret = [];
        for(const k in p){
          let v = p[k]
          if (v === null || typeof v === undefined)
            continue
          if (!Array.isArray(v)) {
            v = [v]
          }
          for(const vv of v){
            ret.push(encodeURIComponent(k)+'='+encodeURIComponent(vv))
          }
        }
        return ret.join('&')
      }
    });
    console.log('pubs resp:')
    console.log(response.data)
    return response.data['publications'];
  };
  
  // get data from server in parallel
  let filter_defaults_fut = axios.get(baseurl+'/api/filter_defaults');
  let publication_types_fut = (async function(){
    const response = await axios.get(baseurl+'/api/types');
    console.log('publication_types:')
    console.log(response.data)
    return response.data;
  })();
  let projects_fut = (async function(){
    const response = await axios.get(baseurl+'/api/projects');
    console.log('projects:')
    console.log(response.data)
    return response.data;
  })();

  // merge default filters
  const response = await filter_defaults_fut;
  var filters_with_defaults = response.data;
  Object.assign(filters_with_defaults, filters);

  // get publications
  let pubs_fut = updatePubs(filters);

  let publication_types = await publication_types_fut;
  let projects = await projects_fut;
  let pubs = await pubs_fut;

  Vue.component('pub', {
    props: {
      title: '',
      authors: '',
      type: '',
      citation: '',
      date: '',
      downloads: [],
      projects: [],
      sites: '',
      project_labels: {},
    },
    methods: {
      getDomain: function(u){
        try {
          if (!u.startsWith('http://') && !u.startsWith('https://') && !u.startsWith('://')) {
            u = 'http://'+u
          }
          return (new URL(u)).hostname;
        } catch {
          return u
        }
      }
    },
    template: `
<article class="publication">
  <div><span class="title">{{ title }}</span></div>
  <div><span class="authors" v-for="author in authors"><span class="author">{{ author }}</span></span></div>
  <div><span class="type">({{ type }})</span>
  <span class="citation">{{ citation }}</span>
  <span class="date">{{ date }}</span></div>
  <div>
    <span class="downloads" v-if="downloads">Download:
      <span class="download" v-for="link in downloads"><a :href="link" target="_blank">{{ getDomain(link) }}</a></span>
    </span>
    <span class="projects" v-if="projects">Project:
      <span class="project" v-for="project in projects">{{ project_labels[project] }}</span>
    </span>
  </div>
</article>`
  });

  // write html
  if (id[0] == '#') {
    document.getElementById(id.substr(1)).innerHTML = pub_html;
  } else {
    console.error('bad id: '+id);
  }

  // start Vue
  var app = new Vue({
    el: id,
    data: {
      filters: filters_with_defaults,
      pubs: pubs,
      publication_types: publication_types,
      projects: projects,
      refresh: 0,
      typing: ''
    },
    watch: {
      filters: {
        handler: function(newFilters, oldFilters) {
          console.log("debouncing")
          this.typing = '...'
          this.debouncedUpdate()
        },
        deep: true
      },
    },
    created: function() {
      this.debouncedUpdate = _.debounce(this.update, 250)
    },
    methods: {
      update: async function() {
        const params = JSON.parse(JSON.stringify( this.filters ));
        const ret = await updatePubs(params);
        this.pubs = ret;
        this.typing = '';
      },
      type_disabled: function(t){
        try {
          return (this.filters.type.length > 0 && this.filters.type[0] != t)
        } catch {
          return false
        }
      }
    }
  });
}